"""
Risk Service — orchestrates risk analysis for a wallet.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain import get_provider
from app.blockchain.mock_provider import MockBlockchainProvider
from app.blockchain.base import RawTransaction
from app.analytics.graph_engine import GraphEngine
from app.analytics.risk_engine import RiskEngine
from app.models import Wallet, Transaction
from app.schemas.schemas import (
    RiskAnalysisResponse, FeatureContribution as FCSchema,
    RiskEvidence as RESchema,
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def analyze_wallet_risk(
    db: AsyncSession,
    case_id: str,
    wallet_address: str,
) -> RiskAnalysisResponse:
    """
    Full risk analysis pipeline:
    1. Load transactions from DB (already fetched by graph service)
    2. Extract graph features
    3. Score with RiskEngine
    4. Persist results to Wallet record
    5. Return RiskAnalysisResponse
    """
    addr = wallet_address.strip().lower()
    case_id_str = str(case_id)

    result = await db.execute(
        select(Transaction).where(Transaction.case_id == case_id_str)
    )
    db_transactions = result.scalars().all()

    # Convert DB transactions to RawTransaction for graph engine
    raw_txns: list[RawTransaction] = []
    for t in db_transactions:
        from datetime import datetime
        raw_txns.append(RawTransaction(
            tx_hash=t.tx_hash,
            from_address=t.from_address,
            to_address=t.to_address,
            amount_eth=t.amount_eth,
            amount_usd=t.amount_usd,
            block_number=t.block_number or 0,
            timestamp=t.timestamp,
            gas_used=t.gas_used or 21000,
            gas_price_gwei=t.gas_price_gwei or 20.0,
            chain=t.chain,
            raw={
                "risk_flags": t.risk_flags or [],
                "hop_number": t.hop_number,
            },
        ))

    if not raw_txns:
        # Fallback: fetch from provider
        provider = get_provider()
        raw_txns = await provider.get_transactions(addr, max_hops=4)

    # Build wallet metadata
    provider = get_provider()
    wallet_meta: dict[str, dict] = {}
    if isinstance(provider, MockBlockchainProvider):
        from app.blockchain.mock_provider import _WALLETS
        all_addrs = {t.from_address.lower() for t in raw_txns} | {t.to_address.lower() for t in raw_txns}
        for a in all_addrs:
            if a in _WALLETS:
                w = _WALLETS[a]
                wallet_meta[a] = {"label": w.get("label", a[:16]), "type": w.get("type", "unknown"), "tags": w.get("tags", [])}
            else:
                wallet_meta[a] = {"label": a[:16], "type": "unknown", "tags": []}

    # Get risk labels
    risk_labels = []
    if isinstance(provider, MockBlockchainProvider):
        risk_labels = provider.get_risk_labels()

    # Build graph and extract features
    engine = GraphEngine(seed_address=addr, transactions=raw_txns, wallet_metadata=wallet_meta)
    engine.build()
    features = engine.extract_features(addr)

    # Score
    risk_engine = RiskEngine(risk_labels=risk_labels)
    analysis = risk_engine.analyze(
        wallet_address=addr,
        features=features,
        transactions=[
            {"tx_hash": t.tx_hash, "is_suspicious": t.is_suspicious, "risk_flags": t.risk_flags or []}
            for t in db_transactions
        ],
    )

    # Persist to wallet record
    wallet_result = await db.execute(
        select(Wallet).where(Wallet.case_id == case_id_str, Wallet.address == addr)
    )
    wallet_obj = wallet_result.scalar_one_or_none()
    if wallet_obj:
        from app.models import RiskLevel
        level_map = {"low": RiskLevel.LOW, "medium": RiskLevel.MEDIUM, "high": RiskLevel.HIGH, "critical": RiskLevel.CRITICAL}
        wallet_obj.risk_score = analysis.risk_score
        wallet_obj.risk_level = level_map.get(analysis.risk_level, RiskLevel.LOW)
        wallet_obj.risk_metadata = {
            "raw_features": analysis.raw_features,
            "confidence": analysis.confidence,
            "uncertainty_notes": analysis.uncertainty_notes,
        }
        wallet_obj.transaction_count = analysis.transaction_count
        wallet_obj.total_sent_usd = analysis.total_volume_usd
        await db.flush()

    return RiskAnalysisResponse(
        wallet_address=addr,
        case_id=case_id_str,
        risk_score=analysis.risk_score,
        risk_level=analysis.risk_level,
        feature_contributions=[
            FCSchema(
                feature=fc.feature,
                value=fc.value,
                normalized_value=fc.normalized_value,
                weight=fc.weight,
                contribution=fc.contribution,
                description=fc.description,
                is_suspicious=fc.is_suspicious,
            ) for fc in analysis.feature_contributions
        ],
        evidence=[
            RESchema(
                evidence_type=e.evidence_type,
                description=e.description,
                severity=e.severity,
                tx_hashes=e.tx_hashes,
            ) for e in analysis.evidence
        ],
        confidence=analysis.confidence,
        uncertainty_notes=analysis.uncertainty_notes,
        analyzed_at=analysis.analyzed_at,
        transaction_count=analysis.transaction_count,
        total_volume_usd=analysis.total_volume_usd,
    )

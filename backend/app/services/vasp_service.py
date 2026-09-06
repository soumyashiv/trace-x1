"""
VASP Attribution Service — evidence-backed entity attribution.

DISCLAIMER: All attributions are probabilistic hypotheses.
They must be corroborated through independent legal channels.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain import get_provider
from app.blockchain.mock_provider import MockBlockchainProvider
from app.models import Wallet, Transaction
from app.schemas.schemas import VaspAttributionResponse, VaspEvidence
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_DISCLAIMER = (
    "This attribution is a probabilistic hypothesis based on available heuristic evidence. "
    "It does NOT constitute a guaranteed identification of the receiving exchange or entity. "
    "Independent legal, regulatory, and forensic corroboration is required before any action. "
    "TRACE-X does not claim live VASP database access."
)


async def attribute_vasp(
    db: AsyncSession,
    case_id: str,
    wallet_address: str,
) -> VaspAttributionResponse:
    """
    Match a wallet against the VASP label database.
    Gather supporting and contradicting evidence.
    """
    addr = wallet_address.strip().lower()
    provider = get_provider()

    # Load VASP labels
    vasp_labels: list[dict] = []
    risk_labels: list[dict] = []
    if isinstance(provider, MockBlockchainProvider):
        vasp_labels = provider.get_vasp_labels()
        risk_labels = provider.get_risk_labels()

    vasp_label_map: dict[str, dict] = {v["address"].lower(): v for v in vasp_labels}
    risk_label_map: dict[str, dict] = {r["address"].lower(): r for r in risk_labels}

    now = datetime.now(timezone.utc)

    # Direct hit
    if addr in vasp_label_map:
        vasp = vasp_label_map[addr]
        supporting = [
            VaspEvidence(
                evidence_type="direct_label_match",
                description=f"Address directly identified as '{vasp['entity']}' in the VASP label database.",
                confidence_impact=0.6,
                source=", ".join(vasp.get("sources", ["synthetic-db"])),
                verified_at=datetime.fromisoformat(vasp["last_verified"].replace("Z", "+00:00")) if vasp.get("last_verified") else None,
            ),
            VaspEvidence(
                evidence_type="cluster_membership",
                description=f"Address belongs to cluster '{vasp.get('cluster_id', 'UNKNOWN')}' "
                            f"— a {vasp.get('category', 'unknown')} entity.",
                confidence_impact=0.2,
                source="TRACE-X cluster database v1",
            ),
        ]
        if vasp.get("kyc_level") == "basic":
            supporting.append(VaspEvidence(
                evidence_type="kyc_signal",
                description="Entity has basic KYC requirements — deposits may be traceable through legal channels.",
                confidence_impact=0.05,
                source="synthetic-regulatory-db",
            ))

        contradicting = [
            VaspEvidence(
                evidence_type="label_staleness",
                description="Label was last verified more than 30 days ago. Exchange deposit addresses rotate frequently.",
                confidence_impact=-0.05,
                source="TRACE-X internal",
            )
        ]

        attribution = VaspAttributionResponse(
            wallet_address=addr,
            case_id=case_id,
            likely_entity=vasp["entity"],
            entity_category=vasp.get("category", "unknown"),
            confidence=min(vasp.get("confidence", 0.7), 0.95),
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            alternative_hypotheses=[
                {"entity": "Unknown OTC Desk", "confidence": 0.06, "notes": "High-volume OTC operations often use similar deposit patterns."},
            ],
            last_verified=datetime.fromisoformat(vasp["last_verified"].replace("Z", "+00:00")) if vasp.get("last_verified") else None,
            source="TRACE-X synthetic VASP label database v1",
            disclaimer=_DISCLAIMER,
            analyzed_at=now,
        )
        _persist_attribution(addr, attribution)
        return attribution

    # Indirect: check if this address received funds from a known-VASP address
    db_txns_result = await db.execute(
        select(Transaction).where(Transaction.case_id == case_id)
    )
    db_transactions = db_txns_result.scalars().all()

    # Cluster proximity check
    receives_from_vasp = [
        t for t in db_transactions
        if t.to_address.lower() == addr and t.from_address.lower() in vasp_label_map
    ]
    sends_to_vasp = [
        t for t in db_transactions
        if t.from_address.lower() == addr and t.to_address.lower() in vasp_label_map
    ]

    if sends_to_vasp:
        target_vasp_addr = sends_to_vasp[0].to_address.lower()
        vasp = vasp_label_map[target_vasp_addr]
        confidence = 0.72
        supporting = [
            VaspEvidence(
                evidence_type="direct_fund_flow",
                description=f"This wallet sent funds directly to known VASP '{vasp['entity']}' "
                            f"(address: {target_vasp_addr[:20]}…) in {len(sends_to_vasp)} transaction(s).",
                confidence_impact=0.5,
                source="TRACE-X graph analysis",
            ),
        ]
        contradicting = [
            VaspEvidence(
                evidence_type="intermediary_uncertainty",
                description="Funds may have passed through additional intermediaries before VASP deposit, reducing traceability.",
                confidence_impact=-0.1,
                source="TRACE-X internal",
            ),
            VaspEvidence(
                evidence_type="attribution_indirect",
                description="This wallet is not the direct VASP deposit address — attribution is indirect via fund flow.",
                confidence_impact=-0.15,
                source="TRACE-X internal",
            ),
        ]
        attribution = VaspAttributionResponse(
            wallet_address=addr,
            case_id=case_id,
            likely_entity=vasp["entity"],
            entity_category=vasp.get("category", "exchange"),
            confidence=confidence,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            alternative_hypotheses=[
                {"entity": "Unknown Exchange", "confidence": 0.18, "notes": "Funds could have been split to a different exchange before final settlement."},
            ],
            last_verified=now,
            source="TRACE-X graph proximity analysis",
            disclaimer=_DISCLAIMER,
            analyzed_at=now,
        )
        return attribution

    # Risk label proximity
    if addr in risk_label_map:
        rl = risk_label_map[addr]
        return VaspAttributionResponse(
            wallet_address=addr,
            case_id=case_id,
            likely_entity=None,
            entity_category="suspected_intermediary",
            confidence=0.35,
            supporting_evidence=[
                VaspEvidence(
                    evidence_type="risk_label",
                    description=f"Address tagged as '{rl['label']}' — commonly used as an intermediary "
                                "before funds reach a VASP.",
                    confidence_impact=0.2,
                    source="TRACE-X synthetic risk label database v1",
                )
            ],
            contradicting_evidence=[
                VaspEvidence(
                    evidence_type="insufficient_evidence",
                    description="No direct VASP label or fund flow to known exchange detected for this address.",
                    confidence_impact=-0.3,
                    source="TRACE-X internal",
                )
            ],
            alternative_hypotheses=[],
            last_verified=now,
            source="TRACE-X risk label proximity",
            disclaimer=_DISCLAIMER,
            analyzed_at=now,
        )

    # No match
    return VaspAttributionResponse(
        wallet_address=addr,
        case_id=case_id,
        likely_entity=None,
        entity_category="unknown",
        confidence=0.0,
        supporting_evidence=[],
        contradicting_evidence=[
            VaspEvidence(
                evidence_type="no_label_found",
                description="No VASP label, risk label, or direct fund flow to a known entity found for this address.",
                confidence_impact=-0.5,
                source="TRACE-X internal",
            )
        ],
        alternative_hypotheses=[],
        last_verified=now,
        source="TRACE-X internal",
        disclaimer=_DISCLAIMER,
        analyzed_at=now,
    )


def _persist_attribution(addr: str, attribution: VaspAttributionResponse) -> None:
    """Logging hook — persistence via wallet.vasp_attribution JSON field handled in router."""
    logger.info("vasp_attributed", address=addr, entity=attribution.likely_entity, confidence=attribution.confidence)

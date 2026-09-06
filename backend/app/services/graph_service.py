"""
Graph Service — orchestrates blockchain data fetching and graph construction.
Applies Redis caching to avoid repeated blockchain queries.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain import get_provider
from app.blockchain.mock_provider import MockBlockchainProvider
from app.analytics.graph_engine import GraphEngine
from app.models import Wallet, Transaction, WalletType, RiskLevel
from app.schemas.schemas import GraphResponse, GraphNode, GraphEdge
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def _get_cache(redis_client, key: str) -> Optional[dict]:
    if not redis_client:
        return None
    try:
        val = await redis_client.get(key)
        if val:
            return json.loads(val)
    except Exception as e:
        logger.warning("cache_read_failed", key=key, error=str(e))
    return None


async def _set_cache(redis_client, key: str, data: dict, ttl: int = 300) -> None:
    if not redis_client:
        return
    try:
        await redis_client.setex(key, ttl, json.dumps(data, default=str))
    except Exception as e:
        logger.warning("cache_write_failed", key=key, error=str(e))


async def build_graph(
    db: AsyncSession,
    case_id: str,
    wallet_address: str,
    max_hops: int = 4,
    redis_client=None,
) -> GraphResponse:
    """
    Main entry point.
    1. Check Redis cache
    2. Fetch transactions from blockchain provider
    3. Persist wallets + transactions to DB
    4. Build graph via GraphEngine
    5. Cache result
    6. Return GraphResponse
    """
    cache_key = f"graph:{case_id}:{wallet_address}:{max_hops}"
    cached = await _get_cache(redis_client, cache_key)
    if cached:
        logger.info("graph_cache_hit", wallet=wallet_address)
        return GraphResponse(**cached)

    provider = get_provider()
    logger.info("graph_building", wallet=wallet_address, provider=provider.provider_name)

    transactions = await provider.get_transactions(
        address=wallet_address,
        max_hops=max_hops,
    )

    all_addresses: set[str] = {wallet_address.lower()}
    for tx in transactions:
        all_addresses.add(tx.from_address.lower())
        all_addresses.add(tx.to_address.lower())

    # Get wallet info (from provider or mock labels)
    wallet_meta: dict[str, dict] = {}
    if isinstance(provider, MockBlockchainProvider):
        from app.blockchain.mock_provider import _WALLETS, _SEED
        for addr in all_addresses:
            if addr in _WALLETS:
                w = _WALLETS[addr]
                wallet_meta[addr] = {
                    "label": w.get("label", addr[:16]),
                    "type": w.get("type", "unknown"),
                    "tags": w.get("tags", []),
                }
            else:
                wallet_meta[addr] = {"label": addr[:16], "type": "unknown", "tags": []}
    else:
        for addr in all_addresses:
            info = await provider.get_wallet_info(addr)
            wallet_meta[addr] = {
                "label": addr[:16],
                "type": "unknown",
                "tags": info.tags,
            }

    case_id_str = str(case_id)
    existing_wallets = {}
    for addr in all_addresses:
        result = await db.execute(
            select(Wallet).where(Wallet.case_id == case_id_str, Wallet.address == addr)
        )
        existing = result.scalar_one_or_none()
        if not existing:
            meta = wallet_meta.get(addr, {})
            type_str = meta.get("type", "unknown")
            wallet_type_map = {
                "victim": WalletType.VICTIM,
                "suspect": WalletType.SUSPECT,
                "intermediary": WalletType.INTERMEDIARY,
                "exchange": WalletType.EXCHANGE,
            }
            w = Wallet(
                case_id=case_id_str,
                address=addr,
                chain="ethereum",
                wallet_type=wallet_type_map.get(type_str, WalletType.UNKNOWN),
                label=meta.get("label"),
                is_seed=(addr == wallet_address.lower()),
            )
            db.add(w)
            await db.flush()
            await db.refresh(w)
            existing_wallets[addr] = w
        else:
            existing_wallets[addr] = existing

    # Persist transactions to DB
    for tx in transactions:
        result = await db.execute(
            select(Transaction).where(
                Transaction.case_id == case_id_str, Transaction.tx_hash == tx.tx_hash
            )
        )
        if not result.scalar_one_or_none():
            risk_flags = tx.raw.get("risk_flags", []) if tx.raw else []
            t = Transaction(
                tx_hash=tx.tx_hash,
                case_id=case_id_str,
                from_address_id=getattr(existing_wallets.get(tx.from_address.lower()), "id", None),
                to_address_id=getattr(existing_wallets.get(tx.to_address.lower()), "id", None),
                from_address=tx.from_address,
                to_address=tx.to_address,
                amount_eth=tx.amount_eth,
                amount_usd=tx.amount_usd,
                gas_used=tx.gas_used,
                gas_price_gwei=tx.gas_price_gwei,
                block_number=tx.block_number,
                timestamp=tx.timestamp,
                chain=tx.chain,
                is_suspicious=bool(risk_flags),
                risk_flags=risk_flags,
                hop_number=tx.raw.get("hop_number") if tx.raw else None,
            )
            db.add(t)

    await db.flush()

    # Build graph
    engine = GraphEngine(
        seed_address=wallet_address,
        transactions=transactions,
        wallet_metadata=wallet_meta,
    )
    result_graph = engine.build()

    # Build response
    now = datetime.now(timezone.utc)
    response = GraphResponse(
        case_id=case_id_str,
        seed_wallet=wallet_address,
        nodes=[GraphNode(**n) for n in result_graph.nodes],
        edges=[
            GraphEdge(
                **{**e, "timestamp": datetime.fromisoformat(e["timestamp"]) if isinstance(e["timestamp"], str) else e["timestamp"]}
            )
            for e in result_graph.edges
        ],
        suspicious_paths=result_graph.suspicious_paths,
        statistics=result_graph.statistics,
        generated_at=now,
    )

    await _set_cache(redis_client, cache_key, response.model_dump())
    return response

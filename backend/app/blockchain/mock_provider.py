"""
Mock Blockchain Provider — deterministic offline demo.

Loads data from seed/demo_data.json.
All responses are deterministic and reproducible.
This provider never makes network calls.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from app.blockchain.base import BlockchainProvider, RawTransaction, WalletInfo
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "seed", "demo_data.json")


def _load_seed() -> dict:
    path = os.path.abspath(_SEED_PATH)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


_SEED: dict = _load_seed()
_WALLETS: dict[str, dict] = {w["address"]: w for w in _SEED["wallets"]}
_TRANSACTIONS: list[dict] = _SEED["transactions"]


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class MockBlockchainProvider(BlockchainProvider):
    """
    Deterministic mock provider.
    Returns synthetic data from demo_data.json.
    Suitable for offline demonstration and testing.
    """

    @property
    def provider_name(self) -> str:
        return "MockBlockchainProvider (synthetic demo data)"

    @property
    def is_live(self) -> bool:
        return False

    async def get_wallet_info(self, address: str, chain: str = "ethereum") -> WalletInfo:
        addr = address.strip().lower()
        wallet = _WALLETS.get(addr)
        if wallet is None:
            # Return a generic unknown wallet rather than raising
            logger.warning("mock_wallet_not_found", address=addr)
            return WalletInfo(
                address=addr,
                chain=chain,
                balance_eth=0.0,
                balance_usd=0.0,
                transaction_count=0,
                first_seen=None,
                last_seen=None,
                is_contract=False,
                tags=["unknown"],
            )

        return WalletInfo(
            address=addr,
            chain=wallet.get("chain", chain),
            balance_eth=wallet.get("balance_eth", 0.0),
            balance_usd=wallet.get("balance_usd", 0.0),
            transaction_count=wallet.get("transaction_count", 0),
            first_seen=_parse_dt(wallet["first_seen"]) if wallet.get("first_seen") else None,
            last_seen=_parse_dt(wallet["last_seen"]) if wallet.get("last_seen") else None,
            is_contract=wallet.get("is_contract", False),
            tags=wallet.get("tags", []),
        )

    async def get_transactions(
        self,
        address: str,
        chain: str = "ethereum",
        max_hops: int = 3,
        max_txns_per_hop: int = 50,
    ) -> list[RawTransaction]:
        """
        BFS traversal over the synthetic transaction graph.
        Returns all transactions reachable from `address` within `max_hops`.
        """
        addr = address.strip().lower()
        visited_addresses: set[str] = set()
        frontier = {addr}
        all_txns: list[RawTransaction] = []
        hop = 0

        while frontier and hop <= max_hops:
            next_frontier: set[str] = set()
            for current_addr in frontier:
                if current_addr in visited_addresses:
                    continue
                visited_addresses.add(current_addr)

                for tx in _TRANSACTIONS:
                    if tx["from_address"] == current_addr or tx["to_address"] == current_addr:
                        rt = RawTransaction(
                            tx_hash=tx["tx_hash"],
                            from_address=tx["from_address"],
                            to_address=tx["to_address"],
                            amount_eth=tx["amount_eth"],
                            amount_usd=tx["amount_usd"],
                            block_number=tx["block_number"],
                            timestamp=_parse_dt(tx["timestamp"]),
                            gas_used=tx["gas_used"],
                            gas_price_gwei=tx["gas_price_gwei"],
                            chain=tx.get("chain", chain),
                            raw={
                                "hop_number": tx.get("hop_number"),
                                "risk_flags": tx.get("risk_flags", []),
                            },
                        )
                        if rt not in all_txns:
                            all_txns.append(rt)
                        # Expand frontier
                        if tx["from_address"] == current_addr:
                            next_frontier.add(tx["to_address"])
                        else:
                            next_frontier.add(tx["from_address"])

            frontier = next_frontier - visited_addresses
            hop += 1

        logger.info("mock_transactions_fetched", address=addr, count=len(all_txns), hops=hop)
        return all_txns

    async def get_transaction(self, tx_hash: str, chain: str = "ethereum") -> Optional[RawTransaction]:
        for tx in _TRANSACTIONS:
            if tx["tx_hash"] == tx_hash:
                return RawTransaction(
                    tx_hash=tx["tx_hash"],
                    from_address=tx["from_address"],
                    to_address=tx["to_address"],
                    amount_eth=tx["amount_eth"],
                    amount_usd=tx["amount_usd"],
                    block_number=tx["block_number"],
                    timestamp=_parse_dt(tx["timestamp"]),
                    gas_used=tx["gas_used"],
                    gas_price_gwei=tx["gas_price_gwei"],
                    chain=tx.get("chain", chain),
                    raw={"hop_number": tx.get("hop_number"), "risk_flags": tx.get("risk_flags", [])},
                )
        return None

    def get_vasp_labels(self) -> list[dict]:
        """Return the synthetic VASP label database."""
        return _SEED.get("vasp_labels", [])

    def get_risk_labels(self) -> list[dict]:
        """Return the synthetic risk label database."""
        return _SEED.get("risk_labels", [])

"""
Blockchain Provider Abstraction Layer.

All blockchain interaction must go through this interface.
This ensures external API failure does not break the application.
"""
from __future__ import annotations
import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawTransaction:
    """Normalized blockchain transaction."""
    tx_hash: str
    from_address: str
    to_address: str
    amount_eth: float
    amount_usd: float
    block_number: int
    timestamp: datetime
    gas_used: int
    gas_price_gwei: float
    chain: str
    is_contract_call: bool = False
    input_data: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class WalletInfo:
    """Wallet metadata from the blockchain."""
    address: str
    chain: str
    balance_eth: float
    balance_usd: float
    transaction_count: int
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    is_contract: bool
    tags: list[str] = field(default_factory=list)


class BlockchainProvider(abc.ABC):
    """
    Abstract base for all blockchain data providers.

    Implementations:
      - MockBlockchainProvider  — deterministic offline demo
      - EVMBlockchainProvider   — live Ethereum / EVM-compatible chains via Web3.py
    """

    @abc.abstractmethod
    async def get_wallet_info(self, address: str, chain: str = "ethereum") -> WalletInfo:
        """Return high-level wallet metadata."""

    @abc.abstractmethod
    async def get_transactions(
        self,
        address: str,
        chain: str = "ethereum",
        max_hops: int = 3,
        max_txns_per_hop: int = 50,
    ) -> list[RawTransaction]:
        """
        Fetch transactions emanating from or received by `address`.
        Implementations should respect max_hops to avoid infinite traversal.
        """

    @abc.abstractmethod
    async def get_transaction(self, tx_hash: str, chain: str = "ethereum") -> Optional[RawTransaction]:
        """Fetch a single transaction by hash."""

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""

    @property
    @abc.abstractmethod
    def is_live(self) -> bool:
        """True if this provider connects to a live network."""

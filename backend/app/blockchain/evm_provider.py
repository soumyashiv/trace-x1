"""
EVM Blockchain Provider — live data via Web3.py.

IMPORTANT: This provider requires a valid ETH_RPC_URL environment variable.
It is NOT used in the offline demo. Set BLOCKCHAIN_PROVIDER=evm in .env to enable.

Rate limiting and caching are applied externally by the graph service.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.blockchain.base import BlockchainProvider, RawTransaction, WalletInfo
from app.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ETH/USD price — in production, fetch from an oracle (e.g. Chainlink)
_ETH_USD_ESTIMATE = 3170.0


class EVMBlockchainProvider(BlockchainProvider):
    """
    Live EVM blockchain provider.

    Connects to an Ethereum-compatible RPC endpoint via Web3.py.
    Uses Etherscan-compatible API for transaction history when available.

    DISCLAIMER: Full transaction history requires a third-party indexer
    (e.g., Etherscan API, Alchemy, Infura). Raw Web3 RPC alone cannot
    efficiently enumerate all transactions for an address.
    """

    def __init__(self) -> None:
        if not settings.eth_rpc_url:
            raise ValueError("ETH_RPC_URL must be set when using EVMBlockchainProvider.")
        try:
            from web3 import Web3
            self._w3 = Web3(Web3.HTTPProvider(settings.eth_rpc_url))
            if not self._w3.is_connected():
                raise ConnectionError(f"Cannot connect to RPC: {settings.eth_rpc_url}")
            logger.info("evm_provider_connected", rpc=settings.eth_rpc_url[:40])
        except ImportError:
            raise ImportError("web3 package is required for EVMBlockchainProvider. Install: pip install web3")

    @property
    def provider_name(self) -> str:
        return "EVMBlockchainProvider (Web3.py / live)"

    @property
    def is_live(self) -> bool:
        return True

    async def get_wallet_info(self, address: str, chain: str = "ethereum") -> WalletInfo:
        from web3 import Web3
        checksum_addr = Web3.to_checksum_address(address)
        balance_wei = self._w3.eth.get_balance(checksum_addr)
        balance_eth = self._w3.from_wei(balance_wei, "ether")
        tx_count = self._w3.eth.get_transaction_count(checksum_addr)
        code = self._w3.eth.get_code(checksum_addr)
        is_contract = len(code) > 2

        return WalletInfo(
            address=address.lower(),
            chain=chain,
            balance_eth=float(balance_eth),
            balance_usd=float(balance_eth) * _ETH_USD_ESTIMATE,
            transaction_count=tx_count,
            first_seen=None,   # Requires an indexer
            last_seen=None,    # Requires an indexer
            is_contract=is_contract,
            tags=[],
        )

    async def get_transactions(
        self,
        address: str,
        chain: str = "ethereum",
        max_hops: int = 3,
        max_txns_per_hop: int = 50,
    ) -> list[RawTransaction]:
        """
        NOTE: Retrieving full tx history from raw RPC requires an indexer.
        This stub raises NotImplementedError to surface this limitation honestly.
        In production, integrate Etherscan API or Alchemy Enhanced APIs here.
        """
        raise NotImplementedError(
            "Full transaction history retrieval from raw EVM RPC is not implemented. "
            "Integrate an Etherscan/Alchemy/Moralis API adapter for production use."
        )

    async def get_transaction(self, tx_hash: str, chain: str = "ethereum") -> Optional[RawTransaction]:
        from web3 import Web3
        try:
            tx = self._w3.eth.get_transaction(tx_hash)
            receipt = self._w3.eth.get_transaction_receipt(tx_hash)
            block = self._w3.eth.get_block(tx["blockNumber"])
            ts = datetime.fromtimestamp(block["timestamp"], tz=timezone.utc)
            amount_eth = float(self._w3.from_wei(tx["value"], "ether"))

            return RawTransaction(
                tx_hash=tx_hash,
                from_address=tx["from"].lower(),
                to_address=(tx["to"] or "0x0").lower(),
                amount_eth=amount_eth,
                amount_usd=amount_eth * _ETH_USD_ESTIMATE,
                block_number=tx["blockNumber"],
                timestamp=ts,
                gas_used=receipt["gasUsed"],
                gas_price_gwei=float(self._w3.from_wei(tx["gasPrice"], "gwei")),
                chain=chain,
                is_contract_call=len(tx.get("input", "0x")) > 2,
            )
        except Exception as e:
            logger.error("evm_get_transaction_failed", tx_hash=tx_hash, error=str(e))
            return None

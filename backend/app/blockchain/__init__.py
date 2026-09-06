from app.blockchain.base import BlockchainProvider, RawTransaction, WalletInfo
from app.blockchain.mock_provider import MockBlockchainProvider
from app.blockchain.evm_provider import EVMBlockchainProvider
from app.config import get_settings

__all__ = ["BlockchainProvider", "RawTransaction", "WalletInfo", "MockBlockchainProvider", "EVMBlockchainProvider", "get_provider"]


def get_provider() -> BlockchainProvider:
    """Factory — returns the configured blockchain provider."""
    settings = get_settings()
    if settings.blockchain_provider == "evm":
        return EVMBlockchainProvider()
    return MockBlockchainProvider()

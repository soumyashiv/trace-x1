"""Tests for the mock blockchain provider."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import asyncio
from app.blockchain.mock_provider import MockBlockchainProvider


SEED_ADDR = "0xsuspect000000000000000000000000000000001"
EXCHANGE_ADDR = "0xexchange0000000000000000000000000000000001"
UNKNOWN_ADDR = "0xunknown000000000000000000000000"


class TestMockBlockchainProvider:
    def setup_method(self):
        self.provider = MockBlockchainProvider()

    def test_provider_name(self):
        assert "Mock" in self.provider.provider_name

    def test_is_not_live(self):
        assert self.provider.is_live is False

    def test_get_wallet_info_known(self):
        info = asyncio.run(self.provider.get_wallet_info(SEED_ADDR))
        assert info.address == SEED_ADDR
        assert info.transaction_count > 0
        assert info.balance_eth >= 0

    def test_get_wallet_info_unknown(self):
        info = asyncio.run(self.provider.get_wallet_info(UNKNOWN_ADDR))
        assert info.address == UNKNOWN_ADDR.lower()
        assert info.transaction_count == 0

    def test_get_transactions_returns_list(self):
        txns = asyncio.run(self.provider.get_transactions(SEED_ADDR, max_hops=4))
        assert isinstance(txns, list)
        assert len(txns) > 0

    def test_get_transactions_cover_full_path(self):
        txns = asyncio.run(self.provider.get_transactions(SEED_ADDR, max_hops=4))
        addresses = {t.from_address for t in txns} | {t.to_address for t in txns}
        assert EXCHANGE_ADDR in addresses

    def test_get_transactions_hop_limit(self):
        txns_1hop = asyncio.run(self.provider.get_transactions(SEED_ADDR, max_hops=1))
        txns_4hop = asyncio.run(self.provider.get_transactions(SEED_ADDR, max_hops=4))
        # More hops should find at least as many transactions
        assert len(txns_4hop) >= len(txns_1hop)

    def test_get_transaction_by_hash(self):
        tx = asyncio.run(self.provider.get_transaction("0xTX001victim_to_suspect"))
        assert tx is not None
        assert tx.tx_hash == "0xTX001victim_to_suspect"

    def test_get_transaction_not_found(self):
        tx = asyncio.run(self.provider.get_transaction("0xNONEXISTENT"))
        assert tx is None

    def test_vasp_labels_not_empty(self):
        labels = self.provider.get_vasp_labels()
        assert len(labels) > 0
        assert "address" in labels[0]
        assert "entity" in labels[0]
        assert "confidence" in labels[0]

    def test_risk_labels_not_empty(self):
        labels = self.provider.get_risk_labels()
        assert len(labels) > 0
        assert "address" in labels[0]
        assert "label" in labels[0]

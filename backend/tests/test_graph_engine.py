"""Tests for the graph engine."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timezone
from app.analytics.graph_engine import GraphEngine
from app.blockchain.base import RawTransaction


def make_tx(tx_hash, from_addr, to_addr, amount_usd=1000.0, hop=0, flags=None):
    return RawTransaction(
        tx_hash=tx_hash,
        from_address=from_addr,
        to_address=to_addr,
        amount_eth=amount_usd / 3170.0,
        amount_usd=amount_usd,
        block_number=1000000,
        timestamp=datetime(2024, 11, 10, 10, 0, 0, tzinfo=timezone.utc),
        gas_used=21000,
        gas_price_gwei=20.0,
        chain="ethereum",
        raw={"hop_number": hop, "risk_flags": flags or []},
    )


SEED = "0xseed"
BURNER = "0xburner"
INTERM = "0xinterm"
EXCHANGE = "0xexchange"

TXS = [
    make_tx("tx1", SEED, BURNER, 5000.0, hop=0, flags=["phishing"]),
    make_tx("tx2", BURNER, INTERM, 4900.0, hop=1, flags=["layering"]),
    make_tx("tx3", INTERM, EXCHANGE, 4850.0, hop=2, flags=["exchange-deposit"]),
]

WALLET_META = {
    SEED: {"label": "Suspect", "type": "suspect", "tags": ["phishing-operator"]},
    BURNER: {"label": "Burner", "type": "intermediary", "tags": ["burner"]},
    INTERM: {"label": "Intermediary", "type": "intermediary", "tags": ["layering"]},
    EXCHANGE: {"label": "Exchange", "type": "exchange", "tags": ["known-vasp"]},
}


class TestGraphEngine:
    def setup_method(self):
        self.engine = GraphEngine(SEED, TXS, WALLET_META)
        self.result = self.engine.build()

    def test_correct_node_count(self):
        assert len(self.result.nodes) == 4

    def test_correct_edge_count(self):
        assert len(self.result.edges) == 3

    def test_all_nodes_have_required_fields(self):
        for node in self.result.nodes:
            assert "id" in node
            assert "address" in node
            assert "node_type" in node
            assert "is_seed" in node

    def test_seed_node_flagged(self):
        seed_node = next(n for n in self.result.nodes if n["address"] == SEED)
        assert seed_node["is_seed"] is True

    def test_exchange_node_type(self):
        exchange_node = next(n for n in self.result.nodes if n["address"] == EXCHANGE)
        assert exchange_node["node_type"] == "exchange"

    def test_suspicious_paths_found(self):
        assert len(self.result.suspicious_paths) > 0
        # At least one path should start from seed
        seed_paths = [p for p in self.result.suspicious_paths if p[0] == SEED]
        assert len(seed_paths) > 0

    def test_statistics_present(self):
        stats = self.result.statistics
        assert "node_count" in stats
        assert "edge_count" in stats
        assert "total_volume_usd" in stats
        assert stats["node_count"] == 4
        assert stats["edge_count"] == 3

    def test_total_volume_usd_correct(self):
        stats = self.result.statistics
        expected = 5000.0 + 4900.0 + 4850.0
        assert abs(stats["total_volume_usd"] - expected) < 0.01

    def test_suspicious_edge_count_correct(self):
        stats = self.result.statistics
        assert stats["suspicious_edge_count"] == 3  # all edges have risk_flags

    def test_feature_extraction_seed(self):
        features = self.engine.extract_features(SEED)
        assert features["is_seed_node"] == 1.0
        assert features["out_degree"] >= 1.0
        assert features["hop_depth_from_seed"] == 0.0

    def test_feature_extraction_exchange(self):
        features = self.engine.extract_features(EXCHANGE)
        assert features["hop_depth_from_seed"] == 3.0

    def test_empty_transactions(self):
        engine = GraphEngine(SEED, [], {})
        result = engine.build()
        assert len(result.nodes) == 0
        assert len(result.edges) == 0

    def test_edges_have_required_fields(self):
        for edge in self.result.edges:
            assert "id" in edge
            assert "source" in edge
            assert "target" in edge
            assert "amount_usd" in edge
            assert "timestamp" in edge

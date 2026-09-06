"""Tests for the risk engine."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.analytics.risk_engine import RiskEngine, FEATURE_CONFIG


class TestRiskEngine:
    def setup_method(self):
        self.engine = RiskEngine()

    def test_zero_features_gives_low_score(self):
        result = self.engine.analyze("0xtest", {})
        assert result.risk_score == 0.0
        assert result.risk_level == "low"

    def test_high_features_gives_high_score(self):
        features = {
            "transaction_count": 200.0,
            "tx_frequency_per_hour": 20.0,
            "burstiness": 3.0,
            "out_degree": 30.0,
            "in_degree": 30.0,
            "transfer_velocity_usd_per_hour": 50000.0,
            "value_concentration_hhi": 0.95,
            "hop_depth_from_seed": 0.0,
            "known_risk_label_count": 5.0,
            "suspicious_edge_count": 10.0,
            "fan_in_out_ratio": 8.0,
        }
        result = self.engine.analyze("0xtest", features)
        assert result.risk_score >= 70.0
        assert result.risk_level in ("high", "critical")

    def test_feature_contributions_sum_to_score(self):
        features = {
            "transaction_count": 50.0,
            "known_risk_label_count": 2.0,
            "suspicious_edge_count": 3.0,
        }
        result = self.engine.analyze("0xtest", features)
        # All contributions should be non-negative
        for fc in result.feature_contributions:
            assert fc.contribution >= 0.0

    def test_risk_level_boundaries(self):
        assert self.engine._score_to_level(0) == "low"
        assert self.engine._score_to_level(24) == "low"
        assert self.engine._score_to_level(25) == "medium"
        assert self.engine._score_to_level(49) == "medium"
        assert self.engine._score_to_level(50) == "high"
        assert self.engine._score_to_level(74) == "high"
        assert self.engine._score_to_level(75) == "critical"
        assert self.engine._score_to_level(100) == "critical"

    def test_risk_label_boosts_score(self):
        base_features = {"transaction_count": 10.0}
        engine_no_labels = RiskEngine(risk_labels=None)
        engine_with_labels = RiskEngine(risk_labels=[
            {"address": "0xmalicious", "label": "phishing-operator", "confidence": 0.9}
        ])
        score_no_label = engine_no_labels.analyze("0xmalicious", base_features).risk_score
        score_with_label = engine_with_labels.analyze("0xmalicious", base_features).risk_score
        assert score_with_label > score_no_label

    def test_evidence_not_empty_for_suspicious_wallet(self):
        features = {
            "known_risk_label_count": 3.0,
            "burstiness": 2.5,
            "transfer_velocity_usd_per_hour": 15000.0,
        }
        result = self.engine.analyze("0xtest", features)
        assert len(result.evidence) > 0

    def test_uncertainty_notes_always_present(self):
        result = self.engine.analyze("0xtest", {})
        assert len(result.uncertainty_notes) > 0

    def test_confidence_below_1_when_few_transactions(self):
        features = {"transaction_count": 2.0}
        result = self.engine.analyze("0xtest", features)
        assert result.confidence < 1.0

    def test_feature_config_weights_sum_to_reasonable(self):
        total_weight = sum(c["weight"] for c in FEATURE_CONFIG.values())
        assert 0.9 <= total_weight <= 1.1, f"Weights sum to {total_weight}"

    def test_hop_depth_lower_is_riskier(self):
        features_close = {"hop_depth_from_seed": 1.0, "known_risk_label_count": 1.0}
        features_far = {"hop_depth_from_seed": 5.0, "known_risk_label_count": 1.0}
        score_close = self.engine.analyze("0xtest", features_close).risk_score
        score_far = self.engine.analyze("0xtest", features_far).risk_score
        assert score_close > score_far

    def test_score_capped_at_100(self):
        features = {k: 1e9 for k in FEATURE_CONFIG}
        result = self.engine.analyze("0xtest", features)
        assert result.risk_score <= 100.0

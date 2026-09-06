"""
TRACE-X Risk Engine — transparent, explainable feature-based risk scoring.

Every risk score is accompanied by:
  - feature_contributions: which signals drove the score
  - evidence: human-readable explanation of each concern
  - confidence: epistemic uncertainty estimate
  - uncertainty_notes: explicit limitations

No black-box scoring. Every result is auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# ── Feature Definitions ───────────────────────────────────────────────────────

FEATURE_CONFIG: dict[str, dict] = {
    "transaction_count": {
        "weight": 0.06,
        "description": "Number of transactions involving this wallet",
        "thresholds": {"medium": 20, "high": 50, "critical": 100},
        "direction": "higher_is_riskier",
    },
    "tx_frequency_per_hour": {
        "weight": 0.09,
        "description": "Transaction frequency (txns per hour)",
        "thresholds": {"medium": 2, "high": 5, "critical": 10},
        "direction": "higher_is_riskier",
    },
    "burstiness": {
        "weight": 0.10,
        "description": "Transaction burstiness (coefficient of variation of inter-tx intervals)",
        "thresholds": {"medium": 0.5, "high": 1.0, "critical": 2.0},
        "direction": "higher_is_riskier",
    },
    "out_degree": {
        "weight": 0.08,
        "description": "Fan-out: number of distinct outbound counterparties",
        "thresholds": {"medium": 3, "high": 8, "critical": 20},
        "direction": "higher_is_riskier",
    },
    "in_degree": {
        "weight": 0.06,
        "description": "Fan-in: number of distinct inbound counterparties",
        "thresholds": {"medium": 3, "high": 8, "critical": 20},
        "direction": "higher_is_riskier",
    },
    "transfer_velocity_usd_per_hour": {
        "weight": 0.10,
        "description": "Fund transfer velocity (USD moved per hour)",
        "thresholds": {"medium": 1000, "high": 5000, "critical": 20000},
        "direction": "higher_is_riskier",
    },
    "value_concentration_hhi": {
        "weight": 0.07,
        "description": "Value concentration index (Herfindahl-Hirschman Index, 0-1)",
        "thresholds": {"medium": 0.3, "high": 0.6, "critical": 0.9},
        "direction": "higher_is_riskier",
    },
    "hop_depth_from_seed": {
        "weight": 0.08,
        "description": "Distance (hops) from the victim-reported seed wallet",
        "thresholds": {"medium": 2, "high": 4, "critical": 6},
        "direction": "lower_is_riskier",  # closer to seed = more directly implicated
    },
    "known_risk_label_count": {
        "weight": 0.18,
        "description": "Number of known-risk labels (burner, phishing, mule, vasp, etc.)",
        "thresholds": {"medium": 1, "high": 2, "critical": 3},
        "direction": "higher_is_riskier",
    },
    "suspicious_edge_count": {
        "weight": 0.12,
        "description": "Number of transactions with risk flags on this wallet",
        "thresholds": {"medium": 1, "high": 3, "critical": 6},
        "direction": "higher_is_riskier",
    },
    "fan_in_out_ratio": {
        "weight": 0.06,
        "description": "Fan-out to fan-in ratio — high values indicate fund aggregation/dispersal",
        "thresholds": {"medium": 1.5, "high": 3.0, "critical": 6.0},
        "direction": "higher_is_riskier",
    },
}


@dataclass
class FeatureContribution:
    feature: str
    value: float
    normalized_value: float
    weight: float
    contribution: float
    description: str
    is_suspicious: bool


@dataclass
class RiskEvidence:
    evidence_type: str
    description: str
    severity: str
    tx_hashes: list[str] = field(default_factory=list)


@dataclass
class RiskAnalysisResult:
    wallet_address: str
    risk_score: float
    risk_level: str
    feature_contributions: list[FeatureContribution]
    evidence: list[RiskEvidence]
    confidence: float
    uncertainty_notes: list[str]
    analyzed_at: datetime
    transaction_count: int
    total_volume_usd: float
    raw_features: dict[str, float]


class RiskEngine:
    """
    Transparent feature-based risk scoring engine.

    Risk score = Σ (normalized_feature × weight) × 100
    Normalized to [0, 100].
    Every contribution is reported separately.
    """

    def __init__(self, risk_labels: list[dict] | None = None):
        """
        Args:
            risk_labels: Optional external label database entries.
                         List of {address, label, confidence} dicts.
        """
        self.risk_label_db: dict[str, dict] = {}
        if risk_labels:
            for entry in risk_labels:
                self.risk_label_db[entry["address"].lower()] = entry

    def analyze(
        self,
        wallet_address: str,
        features: dict[str, float],
        transactions: list[dict] | None = None,
    ) -> RiskAnalysisResult:
        """
        Score a wallet based on extracted graph features.

        Args:
            wallet_address: The address being scored.
            features: Feature dict from GraphEngine.extract_features().
            transactions: Optional list of transaction dicts for evidence generation.
        """
        addr = wallet_address.lower()
        contributions: list[FeatureContribution] = []

        # Augment features with risk label from DB
        if addr in self.risk_label_db:
            entry = self.risk_label_db[addr]
            label = entry.get("label", "")
            label_risk_map = {
                "phishing-operator": 3.0,
                "burner-wallet": 2.5,
                "money-mule": 2.0,
                "aggregator": 1.5,
            }
            added = label_risk_map.get(label, 1.0)
            features = dict(features)
            features["known_risk_label_count"] = features.get("known_risk_label_count", 0) + added

        total_score = 0.0
        total_weight = 0.0

        for feat_name, config in FEATURE_CONFIG.items():
            raw_val = features.get(feat_name, -1.0 if feat_name == "hop_depth_from_seed" else 0.0)
            weight = config["weight"]
            direction = config["direction"]
            thresholds = config["thresholds"]

            # Normalize to [0, 1] based on critical threshold
            crit = thresholds["critical"]
            if direction == "higher_is_riskier":
                normalized = min(raw_val / crit, 1.0) if crit > 0 else 0.0
            else:
                # lower_is_riskier: e.g. hop_depth — being closer means higher risk
                if raw_val < 0:
                    normalized = 0.0  # -1 means unreachable
                else:
                    normalized = max(0.0, 1.0 - (raw_val / crit))

            contribution = normalized * weight
            total_score += contribution
            total_weight += weight

            is_suspicious = normalized >= 0.5
            contributions.append(
                FeatureContribution(
                    feature=feat_name,
                    value=round(raw_val, 4),
                    normalized_value=round(normalized, 4),
                    weight=weight,
                    contribution=round(contribution, 4),
                    description=config["description"],
                    is_suspicious=is_suspicious,
                )
            )

        # Normalize to 0-100
        if total_weight > 0:
            risk_score = min((total_score / total_weight) * 100, 100.0)
        else:
            risk_score = 0.0

        risk_level = self._score_to_level(risk_score)

        # Build evidence list
        evidence = self._build_evidence(addr, contributions, features, transactions or [])

        # Confidence estimation
        confidence, uncertainty_notes = self._estimate_confidence(features, addr)

        result = RiskAnalysisResult(
            wallet_address=addr,
            risk_score=round(risk_score, 2),
            risk_level=risk_level,
            feature_contributions=contributions,
            evidence=evidence,
            confidence=round(confidence, 3),
            uncertainty_notes=uncertainty_notes,
            analyzed_at=datetime.now(timezone.utc),
            transaction_count=int(features.get("transaction_count", 0)),
            total_volume_usd=round(features.get("total_volume_usd", 0.0), 2),
            raw_features=features,
        )

        logger.info(
            "risk_analysis_complete",
            address=addr,
            score=result.risk_score,
            level=risk_level,
            confidence=confidence,
        )
        return result

    @staticmethod
    def _score_to_level(score: float) -> str:
        if score >= 75:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 25:
            return "medium"
        return "low"

    def _build_evidence(
        self,
        address: str,
        contributions: list[FeatureContribution],
        features: dict[str, float],
        transactions: list[dict],
    ) -> list[RiskEvidence]:
        evidence: list[RiskEvidence] = []

        # High-contribution feature evidence
        for c in sorted(contributions, key=lambda x: -x.contribution):
            if c.contribution < 0.02:
                continue
            if c.is_suspicious:
                sev = "critical" if c.normalized_value > 0.8 else "high" if c.normalized_value > 0.5 else "medium"
                evidence.append(RiskEvidence(
                    evidence_type="feature_signal",
                    description=f"{c.description}: observed value {c.value:.2f} "
                                f"(normalized risk contribution: {c.contribution:.2%})",
                    severity=sev,
                ))

        # Known risk label evidence
        if address in self.risk_label_db:
            entry = self.risk_label_db[address]
            evidence.append(RiskEvidence(
                evidence_type="known_label",
                description=f"Address is tagged as '{entry['label']}' in the risk label database "
                            f"(confidence: {entry.get('confidence', 0):.0%}). "
                            "Source: TRACE-X synthetic label database v1.",
                severity="critical",
            ))

        # Suspicious transaction evidence
        sus_txns = [tx for tx in transactions if tx.get("is_suspicious") or tx.get("risk_flags")]
        if sus_txns:
            evidence.append(RiskEvidence(
                evidence_type="suspicious_transactions",
                description=f"{len(sus_txns)} transaction(s) carry risk flags: "
                            + ", ".join(str(t.get("risk_flags", [])) for t in sus_txns[:3]),
                severity="high",
                tx_hashes=[t.get("tx_hash", "") for t in sus_txns[:10]],
            ))

        # Burst activity evidence
        burstiness = features.get("burstiness", 0)
        if burstiness > 1.0:
            evidence.append(RiskEvidence(
                evidence_type="burst_activity",
                description=f"Highly bursty transaction pattern (burstiness={burstiness:.2f}). "
                            "Consistent with automated laundering scripts or structured layering.",
                severity="high",
            ))

        # Rapid forwarding evidence
        velocity = features.get("transfer_velocity_usd_per_hour", 0)
        if velocity > 3000:
            evidence.append(RiskEvidence(
                evidence_type="high_velocity",
                description=f"Funds moved at ${velocity:,.0f}/hour. "
                            "High transfer velocity is a key indicator of automated layering.",
                severity="high" if velocity < 10000 else "critical",
            ))

        return evidence

    def _estimate_confidence(
        self, features: dict[str, float], address: str
    ) -> tuple[float, list[str]]:
        """
        Estimate confidence in the risk score.
        Lower confidence when data is sparse or the wallet is unreachable from seed.
        """
        uncertainty_notes: list[str] = []
        confidence = 1.0

        tx_count = features.get("transaction_count", 0)
        if tx_count < 5:
            confidence -= 0.25
            uncertainty_notes.append(
                f"Only {int(tx_count)} transaction(s) observed. Score may be unreliable with limited data."
            )

        if features.get("hop_depth_from_seed", -1) < 0:
            confidence -= 0.15
            uncertainty_notes.append(
                "Wallet is not reachable from the seed address in the current graph. "
                "Score based on available blockchain data only."
            )

        if features.get("known_risk_label_count", 0) == 0:
            confidence -= 0.10
            uncertainty_notes.append(
                "No known risk labels found for this address. "
                "Absence of a label does not imply the address is safe."
            )

        uncertainty_notes.append(
            "This score is derived from synthetic demo data and graph heuristics. "
            "It is NOT a legally certified risk determination."
        )

        return max(0.1, min(confidence, 1.0)), uncertainty_notes

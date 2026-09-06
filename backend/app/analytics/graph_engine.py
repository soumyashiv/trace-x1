"""
TRACE-X Graph Engine — NetworkX-based transaction graph construction and analysis.

Builds a directed weighted multigraph from blockchain transactions.
Computes graph-theoretic features used by the risk engine.
Identifies suspicious paths through the graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import networkx as nx

from app.blockchain.base import RawTransaction
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class GraphAnalysisResult:
    """Full output of the graph engine for a single seed wallet."""
    seed_address: str
    graph: nx.DiGraph
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    suspicious_paths: list[list[str]]
    statistics: dict[str, Any]
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GraphEngine:
    """
    Builds and analyses the transaction graph for a seed wallet address.

    The graph is a directed weighted graph:
      - Nodes: wallet addresses
      - Edges: individual transactions (with amount, timestamp, flags)
    """

    def __init__(self, seed_address: str, transactions: list[RawTransaction], wallet_metadata: dict[str, dict]):
        """
        Args:
            seed_address: The starting wallet address.
            transactions: Flat list of RawTransaction objects fetched from blockchain provider.
            wallet_metadata: Dict mapping address → metadata dict (type, label, risk_labels, etc.)
        """
        self.seed_address = seed_address.strip().lower()
        self.transactions = transactions
        self.wallet_metadata = {k.lower(): v for k, v in wallet_metadata.items()}
        self.G: nx.MultiDiGraph = nx.MultiDiGraph()

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self) -> GraphAnalysisResult:
        """Entry point — build graph, compute features, detect suspicious paths."""
        self._add_nodes_and_edges()
        suspicious_paths = self._find_suspicious_paths()
        stats = self._compute_statistics()

        nodes = [self._serialize_node(n) for n in self.G.nodes()]
        edges = [self._serialize_edge(u, v, k) for u, v, k in self.G.edges(keys=True)]

        result = GraphAnalysisResult(
            seed_address=self.seed_address,
            graph=self.G,
            nodes=nodes,
            edges=edges,
            suspicious_paths=suspicious_paths,
            statistics=stats,
        )
        logger.info(
            "graph_built",
            seed=self.seed_address,
            nodes=len(nodes),
            edges=len(edges),
            suspicious_paths=len(suspicious_paths),
        )
        return result

    def _add_nodes_and_edges(self) -> None:
        """Populate the NetworkX graph from transactions."""
        for tx in self.transactions:
            src = tx.from_address.lower()
            dst = tx.to_address.lower()

            # Add nodes with metadata
            for addr in (src, dst):
                if addr not in self.G.nodes:
                    meta = self.wallet_metadata.get(addr, {})
                    self.G.add_node(
                        addr,
                        address=addr,
                        label=meta.get("label", addr[:12] + "…"),
                        node_type=meta.get("type", "unknown"),
                        risk_labels=meta.get("tags", []),
                        is_seed=(addr == self.seed_address),
                        transaction_count=0,
                        total_volume_usd=0.0,
                        total_volume_eth=0.0,
                    )

            # Accumulate node volumes
            self.G.nodes[src]["transaction_count"] += 1
            self.G.nodes[src]["total_volume_usd"] += tx.amount_usd
            self.G.nodes[src]["total_volume_eth"] += tx.amount_eth
            self.G.nodes[dst]["transaction_count"] += 1

            # Add directed edge (multigraph via unique key = tx_hash)
            risk_flags = tx.raw.get("risk_flags", []) if tx.raw else []
            self.G.add_edge(
                src,
                dst,
                key=tx.tx_hash,
                tx_hash=tx.tx_hash,
                amount_eth=tx.amount_eth,
                amount_usd=tx.amount_usd,
                timestamp=tx.timestamp,
                hop_number=tx.raw.get("hop_number") if tx.raw else None,
                is_suspicious=bool(risk_flags),
                risk_flags=risk_flags,
                weight=tx.amount_usd,
            )

    # ── Suspicious Path Detection ─────────────────────────────────────────────

    def _find_suspicious_paths(self) -> list[list[str]]:
        """
        Identify suspicious fund-flow paths using heuristics:
        1. All simple paths from the seed wallet to known exchange/high-risk nodes.
        2. Paths that pass through burner wallets or layering intermediaries.
        """
        suspicious: list[list[str]] = []

        # Target nodes: exchanges or nodes with risk labels
        target_nodes = [
            n for n, d in self.G.nodes(data=True)
            if d.get("node_type") in ("exchange", "suspect")
            or any(lbl in d.get("risk_labels", []) for lbl in ["known-vasp", "high-velocity", "phishing-operator"])
        ]

        for target in target_nodes:
            if target == self.seed_address:
                continue
            try:
                for path in nx.all_simple_paths(self.G, self.seed_address, target, cutoff=6):
                    suspicious.append(path)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

        # Also flag paths through intermediary chains (layering detection)
        intermediary_nodes = [
            n for n, d in self.G.nodes(data=True)
            if d.get("node_type") == "intermediary"
            or any(lbl in d.get("risk_labels", []) for lbl in ["layering", "burner", "pass-through"])
        ]

        for inode in intermediary_nodes:
            if inode not in self.G.nodes:
                continue
            if nx.has_path(self.G, self.seed_address, inode):
                try:
                    path = nx.shortest_path(self.G, self.seed_address, inode)
                    if path not in suspicious and len(path) > 1:
                        suspicious.append(path)
                except nx.NetworkXNoPath:
                    pass

        # Deduplicate
        unique = []
        seen: set[tuple] = set()
        for p in suspicious:
            key = tuple(p)
            if key not in seen:
                seen.add(key)
                unique.append(p)

        return unique

    # ── Statistics ────────────────────────────────────────────────────────────

    def _compute_statistics(self) -> dict[str, Any]:
        G = self.G
        node_count = G.number_of_nodes()
        edge_count = G.number_of_edges()

        # Degree stats
        in_degrees = dict(G.in_degree())
        out_degrees = dict(G.out_degree())
        max_fan_out = max(out_degrees.values()) if out_degrees else 0
        max_fan_in = max(in_degrees.values()) if in_degrees else 0

        # Volume stats
        total_volume_usd = sum(
            d.get("amount_usd", 0) for _, _, d in G.edges(data=True)
        )

        # Suspicious edge count
        suspicious_edge_count = sum(
            1 for _, _, d in G.edges(data=True) if d.get("is_suspicious")
        )

        # Time span
        timestamps = [
            d["timestamp"] for _, _, d in G.edges(data=True) if "timestamp" in d
        ]
        if timestamps:
            first_tx = min(timestamps)
            last_tx = max(timestamps)
            duration_hours = (last_tx - first_tx).total_seconds() / 3600
        else:
            first_tx = last_tx = None
            duration_hours = 0.0

        # Connectivity
        try:
            is_dag = nx.is_directed_acyclic_graph(G)
        except Exception:
            is_dag = False

        # Centrality of seed node
        try:
            betweenness = nx.betweenness_centrality(G, weight="weight")
            seed_betweenness = betweenness.get(self.seed_address, 0.0)
        except Exception:
            seed_betweenness = 0.0

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "max_fan_out": max_fan_out,
            "max_fan_in": max_fan_in,
            "total_volume_usd": round(total_volume_usd, 2),
            "suspicious_edge_count": suspicious_edge_count,
            "first_transaction": first_tx.isoformat() if first_tx else None,
            "last_transaction": last_tx.isoformat() if last_tx else None,
            "duration_hours": round(duration_hours, 2),
            "is_dag": is_dag,
            "seed_betweenness_centrality": round(seed_betweenness, 4),
        }

    # ── Serialization ─────────────────────────────────────────────────────────

    def _serialize_node(self, node_id: str) -> dict[str, Any]:
        data = dict(self.G.nodes[node_id])
        return {
            "id": node_id,
            "address": node_id,
            "label": data.get("label", node_id[:16]),
            "node_type": data.get("node_type", "unknown"),
            "risk_labels": data.get("risk_labels", []),
            "is_seed": data.get("is_seed", False),
            "transaction_count": data.get("transaction_count", 0),
            "total_volume_usd": round(data.get("total_volume_usd", 0.0), 2),
            "total_volume_eth": round(data.get("total_volume_eth", 0.0), 6),
            "chain": "ethereum",
            "metadata": {},
        }

    def _serialize_edge(self, u: str, v: str, key: str) -> dict[str, Any]:
        data = dict(self.G.edges[u, v, key])
        ts = data.get("timestamp")
        return {
            "id": key,
            "source": u,
            "target": v,
            "tx_hash": data.get("tx_hash", key),
            "amount_eth": data.get("amount_eth", 0.0),
            "amount_usd": data.get("amount_usd", 0.0),
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
            "is_suspicious": data.get("is_suspicious", False),
            "risk_flags": data.get("risk_flags", []),
            "hop_number": data.get("hop_number"),
        }

    # ── Feature Extraction (for Risk Engine) ──────────────────────────────────

    def extract_features(self, address: str) -> dict[str, float]:
        """
        Extract numeric graph features for a wallet address.
        Used as input to the risk scoring engine.
        """
        addr = address.lower()
        G = self.G

        if addr not in G.nodes:
            return {}

        in_deg = G.in_degree(addr)
        out_deg = G.out_degree(addr)

        # Transactions involving this wallet
        out_txns = [(u, v, d) for u, v, d in G.edges(data=True) if u == addr]
        in_txns = [(u, v, d) for u, v, d in G.edges(data=True) if v == addr]
        all_txns = out_txns + in_txns

        volumes = [d.get("amount_usd", 0) for _, _, d in all_txns]
        timestamps = sorted([d["timestamp"] for _, _, d in all_txns if "timestamp" in d])

        # Transaction frequency & burstiness
        if len(timestamps) > 1:
            intervals = [
                (timestamps[i + 1] - timestamps[i]).total_seconds()
                for i in range(len(timestamps) - 1)
            ]
            avg_interval_s = sum(intervals) / len(intervals) if intervals else 0
            # Coefficient of variation = std/mean — high = bursty
            if avg_interval_s > 0:
                import statistics
                std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
                burstiness = std_interval / avg_interval_s
            else:
                burstiness = 1.0
            tx_frequency_per_hour = 3600 / avg_interval_s if avg_interval_s > 0 else 0
        else:
            burstiness = 0.0
            tx_frequency_per_hour = 0.0

        # Transfer velocity (total value / duration)
        if len(timestamps) > 1:
            duration_s = (timestamps[-1] - timestamps[0]).total_seconds()
            total_vol = sum(volumes)
            transfer_velocity = total_vol / (duration_s / 3600) if duration_s > 0 else 0
        else:
            transfer_velocity = 0.0

        # Value concentration (Herfindahl index)
        if volumes:
            total = sum(volumes)
            if total > 0:
                hhi = sum((v / total) ** 2 for v in volumes)
            else:
                hhi = 0.0
        else:
            hhi = 0.0

        # Hop depth from seed
        try:
            if nx.has_path(G, self.seed_address, addr):
                hop_depth = nx.shortest_path_length(G, self.seed_address, addr)
            else:
                hop_depth = -1
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            hop_depth = -1

        # Risk label count
        risk_labels = G.nodes[addr].get("risk_labels", [])
        known_risk_label_count = len([l for l in risk_labels if "burner" in l or "phishing" in l or "mule" in l or "vasp" in l])

        return {
            "transaction_count": float(len(all_txns)),
            "in_degree": float(in_deg),
            "out_degree": float(out_deg),
            "fan_in_out_ratio": float(out_deg) / max(float(in_deg), 1),
            "total_volume_usd": float(sum(volumes)),
            "avg_tx_value_usd": float(sum(volumes) / len(volumes)) if volumes else 0.0,
            "tx_frequency_per_hour": float(tx_frequency_per_hour),
            "burstiness": float(burstiness),
            "transfer_velocity_usd_per_hour": float(transfer_velocity),
            "value_concentration_hhi": float(hhi),
            "hop_depth_from_seed": float(hop_depth),
            "known_risk_label_count": float(known_risk_label_count),
            "is_seed_node": float(addr == self.seed_address),
            "suspicious_edge_count": float(
                sum(1 for _, _, d in all_txns if d.get("is_suspicious"))
            ),
        }

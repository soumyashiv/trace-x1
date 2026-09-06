"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { graphApi, walletsApi } from "@/lib/api";
import type { GraphResponse, GraphNode, GraphEdge, Wallet } from "@/types";
import Header from "@/components/layout/Header";
import {
  ZoomIn, ZoomOut, Maximize2, RefreshCw,
  GitBranch, AlertTriangle, Info, X, ExternalLink
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

// Risk color map for Cytoscape
const NODE_COLORS: Record<string, string> = {
  suspect: "#ef4444",
  victim: "#60a5fa",
  intermediary: "#f59e0b",
  exchange: "#10b981",
  unknown: "#6b7280",
};

const RISK_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#f59e0b",
  low: "#10b981",
};

interface SelectedNode {
  node: GraphNode;
  wallet?: Wallet;
}

export default function GraphPage() {
  const { id } = useParams<{ id: string }>();
  const cyRef = useRef<HTMLDivElement>(null);
  const cyInstance = useRef<unknown>(null);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<SelectedNode | null>(null);
  const [highlightPath, setHighlightPath] = useState<string[]>([]);

  const seedAddress = wallets.find(w => w.is_seed)?.address;

  const loadGraph = useCallback(async () => {
    if (!seedAddress) return;
    setLoading(true);
    try {
      const g = await graphApi.build(id, seedAddress);
      setGraph(g);
    } catch {
      toast.error("Failed to load graph");
    } finally {
      setLoading(false);
    }
  }, [id, seedAddress]);

  useEffect(() => {
    walletsApi.list(id).then(w => setWallets(w));
  }, [id]);

  useEffect(() => {
    if (seedAddress) loadGraph();
  }, [seedAddress, loadGraph]);

  useEffect(() => {
    if (!graph || !cyRef.current) return;
    initCytoscape(graph);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph, highlightPath]);

  const initCytoscape = async (g: GraphResponse) => {
    const cytoscape = (await import("cytoscape")).default;

    if (cyInstance.current) {
      (cyInstance.current as { destroy(): void }).destroy();
    }

    const suspiciousNodes = new Set(g.suspicious_paths.flat());

    const elements = [
      ...g.nodes.map(n => ({
        data: {
          id: n.id,
          label: n.label || n.address.slice(0, 10) + "…",
          address: n.address,
          node_type: n.node_type,
          risk_score: n.risk_score,
          risk_level: n.risk_level,
          is_seed: n.is_seed,
          total_volume_usd: n.total_volume_usd,
          is_suspicious: suspiciousNodes.has(n.id),
          is_highlighted: highlightPath.includes(n.id),
        },
      })),
      ...g.edges.map(e => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          tx_hash: e.tx_hash,
          amount_usd: e.amount_usd,
          is_suspicious: e.is_suspicious,
          risk_flags: e.risk_flags,
          hop_number: e.hop_number,
          is_highlighted: highlightPath.includes(e.source) && highlightPath.includes(e.target),
        },
      })),
    ];

    const cy = cytoscape({
      container: cyRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": (el: { data: (k: string) => string | boolean }) => {
              const rl = el.data("risk_level") as string;
              const nt = el.data("node_type") as string;
              return rl ? RISK_COLORS[rl] : NODE_COLORS[nt] || "#6b7280";
            },
            "border-width": (el: { data: (k: string) => string | boolean }) => el.data("is_seed") ? 4 : el.data("is_suspicious") ? 3 : 1,
            "border-color": (el: { data: (k: string) => string | boolean }) => el.data("is_seed") ? "#a5b4fc" : el.data("is_suspicious") ? "#ef4444" : "rgba(255,255,255,0.2)",
            label: "data(label)",
            color: "#f8fafc",
            "font-size": 10,
            "font-family": "Inter, sans-serif",
            "text-valign": "bottom",
            "text-margin-y": 6,
            "text-outline-color": "#0f172a",
            "text-outline-width": 2,
            width: (el: { data: (k: string) => number }) => Math.max(30, Math.min(60, 30 + (el.data("total_volume_usd") || 0) / 500)),
            height: (el: { data: (k: string) => number }) => Math.max(30, Math.min(60, 30 + (el.data("total_volume_usd") || 0) / 500)),
            "overlay-opacity": 0,
          } as Record<string, unknown>,
        },
        {
          selector: "node:selected",
          style: {
            "border-color": "#6366f1",
            "border-width": 4,
            "box-shadow": "0 0 20px rgba(99,102,241,0.8)",
          } as Record<string, unknown>,
        },
        {
          selector: "edge",
          style: {
            width: (el: { data: (k: string) => number }) => Math.max(1, Math.min(6, (el.data("amount_usd") || 0) / 1500)),
            "line-color": (el: { data: (k: string) => boolean }) => el.data("is_suspicious") ? "#ef4444" : "rgba(99,102,241,0.4)",
            "target-arrow-color": (el: { data: (k: string) => boolean }) => el.data("is_suspicious") ? "#ef4444" : "rgba(99,102,241,0.6)",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: (el: { data: (k: string) => number }) => el.data("amount_usd") ? `$${(el.data("amount_usd") as number).toLocaleString()}` : "",
            "font-size": 9,
            color: "#94a3b8",
            "text-rotation": "autorotate",
            "text-outline-color": "#0f172a",
            "text-outline-width": 2,
            opacity: 0.85,
          } as Record<string, unknown>,
        },
        {
          selector: "edge:selected",
          style: { "line-color": "#6366f1", width: 4, opacity: 1 } as Record<string, unknown>,
        },
      ],
      layout: { name: "breadthfirst", directed: true, spacingFactor: 1.6, padding: 40 },
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });

    cy.on("tap", "node", (evt: { target: { data: (k: string) => unknown } }) => {
      const data = evt.target.data;
      const nodeData: GraphNode = {
        id: data("id") as string,
        address: data("address") as string,
        label: data("label") as string,
        node_type: data("node_type") as GraphNode["node_type"],
        risk_score: data("risk_score") as number | null,
        risk_level: data("risk_level") as GraphNode["risk_level"],
        transaction_count: data("transaction_count") as number || 0,
        total_volume_usd: data("total_volume_usd") as number || 0,
        is_seed: data("is_seed") as boolean,
        chain: "ethereum",
        metadata: {},
      };
      const wallet = wallets.find(w => w.address === nodeData.address);
      setSelected({ node: nodeData, wallet });
    });

    cy.on("tap", (evt: { target: { group?: () => string } }) => {
      if (!evt.target.group) setSelected(null);
    });

    cyInstance.current = cy;
    setTimeout(() => cy.fit(undefined, 40), 100);
  };

  const zoomIn = () => (cyInstance.current as { zoom: (n: number) => void } | null)?.zoom(((cyInstance.current as { zoom: () => number }).zoom()) * 1.3);
  const zoomOut = () => (cyInstance.current as { zoom: (n: number) => void } | null)?.zoom(((cyInstance.current as { zoom: () => number }).zoom()) * 0.7);
  const fitView = () => (cyInstance.current as { fit: (u: undefined, n: number) => void } | null)?.fit(undefined, 40);

  const highlightSuspiciousPath = () => {
    if (!graph) return;
    const longest = graph.suspicious_paths.reduce((a, b) => b.length > a.length ? b : a, []);
    setHighlightPath(longest);
    toast.success(`Highlighted ${longest.length}-hop suspicious path`);
  };

  const riskBadgeClass: Record<string, string> = {
    low: "risk-badge-low", medium: "risk-badge-medium",
    high: "risk-badge-high", critical: "risk-badge-critical",
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header
        title="Transaction Graph"
        subtitle={graph ? `${graph.nodes.length} nodes · ${graph.edges.length} edges · ${graph.suspicious_paths.length} suspicious paths` : "Building graph…"}
        actions={
          <div className="flex gap-2">
            <button onClick={highlightSuspiciousPath} className="btn-secondary flex items-center gap-1.5 text-xs">
              <AlertTriangle size={13} className="text-amber-400" /> Highlight Path
            </button>
            <button onClick={loadGraph} className="btn-secondary flex items-center gap-1.5 text-xs">
              <RefreshCw size={13} /> Refresh
            </button>
          </div>
        }
      />

      <div className="flex-1 flex gap-0 p-4 relative overflow-hidden" style={{ height: "calc(100vh - 73px)" }}>
        {/* Graph canvas */}
        <div className="flex-1 relative rounded-xl overflow-hidden border border-white/5">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center z-10 bg-surface-900/80">
              <div className="text-center">
                <div className="w-12 h-12 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin mx-auto mb-3" />
                <p className="text-surface-400 text-sm">Building transaction graph…</p>
              </div>
            </div>
          )}
          <div id="cy-container" ref={cyRef} style={{ width: "100%", height: "100%" }} />

          {/* Zoom controls */}
          <div className="absolute bottom-4 left-4 flex flex-col gap-2">
            {[
              { icon: ZoomIn, fn: zoomIn, label: "Zoom in" },
              { icon: ZoomOut, fn: zoomOut, label: "Zoom out" },
              { icon: Maximize2, fn: fitView, label: "Fit view" },
            ].map(({ icon: Icon, fn, label }) => (
              <button key={label} onClick={fn} title={label}
                className="w-9 h-9 glass-card flex items-center justify-center hover:border-brand-500/40 transition text-surface-300 hover:text-white">
                <Icon size={16} />
              </button>
            ))}
          </div>

          {/* Legend */}
          <div className="absolute top-4 left-4 glass-card p-3 text-xs space-y-1.5">
            {Object.entries(NODE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ background: color }} />
                <span className="text-surface-400 capitalize">{type}</span>
              </div>
            ))}
            <hr className="border-white/10" />
            <div className="flex items-center gap-2">
              <div className="w-3 h-1 bg-red-500 rounded" />
              <span className="text-surface-400">Suspicious edge</span>
            </div>
          </div>

          {/* Stats overlay */}
          {graph && (
            <div className="absolute top-4 right-4 glass-card p-3 text-xs space-y-1">
              <p className="text-surface-400">Total Volume</p>
              <p className="text-surface-100 font-bold">${graph.statistics.total_volume_usd.toLocaleString()}</p>
              <p className="text-surface-400 mt-1">Suspicious Txns</p>
              <p className="text-red-400 font-bold">{graph.statistics.suspicious_edge_count}</p>
              <p className="text-surface-400 mt-1">Duration</p>
              <p className="text-surface-100">{graph.statistics.duration_hours.toFixed(1)}h</p>
            </div>
          )}
        </div>

        {/* Detail Panel */}
        {selected && (
          <div className="w-72 ml-3 glass-card p-4 overflow-y-auto flex-shrink-0 animate-slide-up">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <GitBranch size={14} className="text-brand-400" />
                <span className="text-sm font-semibold text-surface-100">Wallet Details</span>
              </div>
              <button onClick={() => setSelected(null)} className="text-surface-500 hover:text-surface-200">
                <X size={15} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-[10px] uppercase tracking-wide text-surface-500 mb-1">Address</p>
                <p className="font-mono text-xs text-brand-300 break-all">{selected.node.address}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[10px] uppercase tracking-wide text-surface-500 mb-1">Type</p>
                  <span className="text-xs font-medium capitalize text-surface-200">{selected.node.node_type}</span>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wide text-surface-500 mb-1">Chain</p>
                  <span className="text-xs text-surface-200">{selected.node.chain}</span>
                </div>
              </div>

              {selected.node.risk_level && (
                <div>
                  <p className="text-[10px] uppercase tracking-wide text-surface-500 mb-1">Risk Score</p>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold text-surface-50">{selected.node.risk_score?.toFixed(1)}</span>
                    <span className={clsx("text-xs px-2 py-0.5 rounded-full border font-semibold", riskBadgeClass[selected.node.risk_level])}>
                      {selected.node.risk_level.toUpperCase()}
                    </span>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[10px] uppercase tracking-wide text-surface-500 mb-1">Transactions</p>
                  <span className="text-lg font-bold text-surface-100">{selected.node.transaction_count}</span>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wide text-surface-500 mb-1">Volume (USD)</p>
                  <span className="text-lg font-bold text-surface-100">${selected.node.total_volume_usd.toLocaleString()}</span>
                </div>
              </div>

              {selected.node.is_seed && (
                <div className="p-2.5 rounded-lg bg-brand-500/10 border border-brand-500/20">
                  <p className="text-xs text-brand-300 flex items-center gap-1.5">
                    <Info size={12} /> Seed wallet — victim-reported suspect address
                  </p>
                </div>
              )}

              <div className="pt-2 border-t border-white/5 space-y-2">
                <a href={`https://etherscan.io/address/${selected.node.address}`} target="_blank" rel="noopener noreferrer"
                  className="btn-secondary w-full flex items-center justify-center gap-1.5 text-xs">
                  <ExternalLink size={12} /> View on Etherscan (demo)
                </a>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

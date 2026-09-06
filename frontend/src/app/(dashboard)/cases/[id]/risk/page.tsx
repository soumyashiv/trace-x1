"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { riskApi, walletsApi } from "@/lib/api";
import type { RiskAnalysis, Wallet } from "@/types";
import Header from "@/components/layout/Header";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell
} from "recharts";
import { Shield, AlertTriangle, Info, ChevronDown, ChevronUp } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

const riskBadge: Record<string, string> = {
  low: "risk-badge-low", medium: "risk-badge-medium",
  high: "risk-badge-high", critical: "risk-badge-critical",
};
const riskBar: Record<string, string> = {
  low: "#10b981", medium: "#f59e0b", high: "#f97316", critical: "#ef4444",
};

export default function RiskPage() {
  const { id } = useParams<{ id: string }>();
  const [risk, setRisk] = useState<RiskAnalysis | null>(null);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    walletsApi.list(id).then(async ws => {
      const seed = ws.find(w => w.is_seed) || ws[0];
      if (!seed) return;
      setWallet(seed);
      const r = await riskApi.analyze(id, seed.address).catch(() => null);
      setRisk(r);
    }).catch(() => toast.error("Failed to load risk analysis")).finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-10 h-10 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
    </div>
  );

  const radarData = risk?.feature_contributions.slice(0, 8).map(fc => ({
    feature: fc.feature.replace(/_/g, " ").slice(0, 18),
    value: Math.round(fc.normalized_value * 100),
    fullMark: 100,
  }));

  const barData = risk?.feature_contributions
    .filter(fc => fc.contribution > 0.01)
    .sort((a, b) => b.contribution - a.contribution)
    .slice(0, 10)
    .map(fc => ({
      name: fc.feature.replace(/_/g, " "),
      value: Math.round(fc.contribution * 1000) / 10,
      suspicious: fc.is_suspicious,
    }));

  const sevColors: Record<string, string> = { critical: "text-red-400 bg-red-400/10 border-red-400/20", high: "text-orange-400 bg-orange-400/10 border-orange-400/20", medium: "text-amber-400 bg-amber-400/10 border-amber-400/20", low: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20" };

  return (
    <div className="min-h-screen">
      <Header title="Risk Analysis" subtitle={`Wallet: ${wallet?.address?.slice(0, 24)}…`} />

      <div className="p-6 space-y-6">
        {!risk ? (
          <div className="glass-card p-8 text-center">
            <Shield size={40} className="mx-auto text-surface-600 mb-3" />
            <p className="text-surface-400">No risk analysis available. Run graph analysis first.</p>
          </div>
        ) : (
          <>
            {/* Score Banner */}
            <div className="glass-card p-6 relative overflow-hidden">
              <div className="absolute inset-0 opacity-10" style={{
                background: `radial-gradient(circle at 80% 50%, ${riskBar[risk.risk_level]}, transparent 60%)`
              }} />
              <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                <div>
                  <p className="text-xs text-surface-400 uppercase tracking-widest mb-2">Overall Risk Score</p>
                  <div className="flex items-end gap-4">
                    <span className="text-7xl font-black" style={{ color: riskBar[risk.risk_level] }}>
                      {risk.risk_score.toFixed(1)}
                    </span>
                    <div className="pb-2">
                      <span className={clsx("text-sm px-3 py-1 rounded-full border font-bold", riskBadge[risk.risk_level])}>
                        {risk.risk_level.toUpperCase()}
                      </span>
                      <p className="text-xs text-surface-400 mt-1">Confidence: {(risk.confidence * 100).toFixed(0)}%</p>
                    </div>
                  </div>
                  <div className="w-64 bg-surface-700 rounded-full h-2 mt-3">
                    <div className="h-2 rounded-full transition-all" style={{ width: `${risk.risk_score}%`, background: riskBar[risk.risk_level] }} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="glass-card p-3">
                    <p className="text-xs text-surface-400">Transactions</p>
                    <p className="text-xl font-bold text-surface-100">{risk.transaction_count}</p>
                  </div>
                  <div className="glass-card p-3">
                    <p className="text-xs text-surface-400">Volume (USD)</p>
                    <p className="text-xl font-bold text-surface-100">${risk.total_volume_usd.toLocaleString()}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Bar Chart */}
              <div className="glass-card p-5">
                <h3 className="font-semibold text-surface-100 mb-4">Feature Contributions</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={barData} layout="vertical" margin={{ left: 10, right: 20 }}>
                    <XAxis type="number" domain={[0, 20]} tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={v => `${v}%`} />
                    <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 9 }} width={130} />
                    <Tooltip
                      contentStyle={{ background: "#1e293b", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 12 }}
                      formatter={(v: number) => [`${v}%`, "Contribution"]}
                      labelStyle={{ color: "#f8fafc" }}
                    />
                    <Bar dataKey="value" radius={4}>
                      {barData?.map((entry, i) => (
                        <Cell key={i} fill={entry.suspicious ? "#ef4444" : "#6366f1"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Radar Chart */}
              <div className="glass-card p-5">
                <h3 className="font-semibold text-surface-100 mb-4">Risk Profile Radar</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="rgba(255,255,255,0.08)" />
                    <PolarAngleAxis dataKey="feature" tick={{ fill: "#64748b", fontSize: 8 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#475569", fontSize: 8 }} />
                    <Radar name="Risk" dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.25} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Evidence */}
            <div className="glass-card overflow-hidden">
              <div className="px-5 py-4 border-b border-white/5">
                <h3 className="font-semibold text-surface-100">Evidence ({risk.evidence.length})</h3>
              </div>
              <div className="p-4 space-y-3">
                {risk.evidence.map((ev, i) => (
                  <div key={i} className={clsx("p-4 rounded-xl border", sevColors[ev.severity])}>
                    <div className="flex items-start gap-3">
                      <AlertTriangle size={15} className="mt-0.5 shrink-0" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold uppercase tracking-wide">{ev.evidence_type.replace(/_/g, " ")}</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-black/20">{ev.severity.toUpperCase()}</span>
                        </div>
                        <p className="text-xs leading-relaxed opacity-90">{ev.description}</p>
                        {ev.tx_hashes?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {ev.tx_hashes.slice(0, 3).map(h => (
                              <span key={h} className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-black/20 opacity-75">{h.slice(0, 20)}…</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Feature Details Accordion */}
            <div className="glass-card overflow-hidden">
              <div className="px-5 py-4 border-b border-white/5">
                <h3 className="font-semibold text-surface-100">Feature Breakdown (all {risk.feature_contributions.length} signals)</h3>
              </div>
              <div className="divide-y divide-white/5">
                {risk.feature_contributions.map(fc => (
                  <div key={fc.feature}>
                    <button
                      onClick={() => setExpanded(expanded === fc.feature ? null : fc.feature)}
                      className="w-full px-5 py-3.5 flex items-center justify-between hover:bg-white/[0.02] transition"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full" style={{ background: fc.is_suspicious ? "#ef4444" : "#6366f1" }} />
                        <span className="text-sm text-surface-200 font-medium">{fc.feature.replace(/_/g, " ")}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-xs font-mono text-surface-400">{fc.value.toFixed(3)}</span>
                        <span className="text-xs font-semibold" style={{ color: fc.is_suspicious ? "#ef4444" : "#6366f1" }}>
                          +{(fc.contribution * 100).toFixed(1)}%
                        </span>
                        {expanded === fc.feature ? <ChevronUp size={14} className="text-surface-500" /> : <ChevronDown size={14} className="text-surface-500" />}
                      </div>
                    </button>
                    {expanded === fc.feature && (
                      <div className="px-5 pb-4 bg-black/10">
                        <p className="text-xs text-surface-400 mb-2">{fc.description}</p>
                        <div className="grid grid-cols-3 gap-3 text-xs">
                          <div><p className="text-surface-500">Raw Value</p><p className="font-mono text-surface-200">{fc.value.toFixed(4)}</p></div>
                          <div><p className="text-surface-500">Normalized</p><p className="font-mono text-surface-200">{(fc.normalized_value * 100).toFixed(1)}%</p></div>
                          <div><p className="text-surface-500">Weight</p><p className="font-mono text-surface-200">{(fc.weight * 100).toFixed(0)}%</p></div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Uncertainty Notes */}
            <div className="glass-card p-5">
              <h3 className="font-semibold text-surface-100 mb-3 flex items-center gap-2">
                <Info size={15} className="text-brand-400" /> Uncertainty Notes
              </h3>
              <ul className="space-y-2">
                {risk.uncertainty_notes.map((n, i) => (
                  <li key={i} className="text-xs text-surface-400 flex items-start gap-2">
                    <span className="text-brand-500 mt-0.5">·</span> {n}
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

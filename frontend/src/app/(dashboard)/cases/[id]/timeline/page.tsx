"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { graphApi, walletsApi } from "@/lib/api";
import type { GraphResponse, Wallet } from "@/types";
import Header from "@/components/layout/Header";
import { format } from "date-fns";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Clock, ArrowRight, AlertTriangle } from "lucide-react";
import clsx from "clsx";

export default function TimelinePage() {
  const { id } = useParams<{ id: string }>();
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    walletsApi.list(id).then(async ws => {
      const seed = ws.find(w => w.is_seed) || ws[0];
      if (!seed) return;
      const g = await graphApi.get(id, seed.address).catch(() => null);
      setGraph(g);
    }).finally(() => setLoading(false));
  }, [id]);

  const edges = graph?.edges.slice().sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()) || [];

  const chartData = edges.map(e => ({
    time: format(new Date(e.timestamp), "dd MMM HH:mm"),
    amount_usd: e.amount_usd,
    suspicious: e.is_suspicious ? e.amount_usd : 0,
  }));

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-10 h-10 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen">
      <Header title="Transaction Timeline" subtitle={`${edges.length} transactions in chronological order`} />

      <div className="p-6 space-y-6">
        {/* Area Chart */}
        <div className="glass-card p-5">
          <h3 className="font-semibold text-surface-100 mb-4">Fund Flow Over Time (USD)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="susGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 9 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 9 }} tickFormatter={v => `$${(v / 1000).toFixed(1)}k`} />
              <Tooltip
                contentStyle={{ background: "#1e293b", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 12 }}
                formatter={(v: number) => [`$${v.toLocaleString()}`, ""]}
              />
              <Area type="monotone" dataKey="amount_usd" stroke="#6366f1" fill="url(#totalGrad)" strokeWidth={2} name="Total" />
              <Area type="monotone" dataKey="suspicious" stroke="#ef4444" fill="url(#susGrad)" strokeWidth={2} name="Suspicious" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Timeline */}
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/5">
            <h3 className="font-semibold text-surface-100">Transaction Sequence</h3>
          </div>
          <div className="p-5">
            <div className="relative">
              {/* Vertical line */}
              <div className="absolute left-4 top-0 bottom-0 w-px bg-brand-500/20" />
              <div className="space-y-4 pl-12">
                {edges.map((edge, i) => (
                  <div key={edge.id} className={clsx(
                    "relative p-4 rounded-xl border transition-all",
                    edge.is_suspicious ? "bg-red-500/5 border-red-500/20" : "bg-surface-800/40 border-white/5 hover:border-white/10"
                  )}>
                    {/* Circle on timeline */}
                    <div className={clsx(
                      "absolute -left-8 top-4 w-4 h-4 rounded-full border-2 flex items-center justify-center",
                      edge.is_suspicious ? "bg-red-500 border-red-400" : "bg-brand-500 border-brand-400"
                    )}>
                      <span className="text-[8px] text-white font-bold">{i + 1}</span>
                    </div>

                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Clock size={11} className="text-surface-500" />
                          <span className="text-xs text-surface-400 font-mono">
                            {format(new Date(edge.timestamp), "dd MMM yyyy HH:mm:ss")}
                          </span>
                          {edge.hop_number !== null && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-400 font-medium">
                              Hop {edge.hop_number}
                            </span>
                          )}
                          {edge.is_suspicious && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 font-medium flex items-center gap-1">
                              <AlertTriangle size={10} /> Suspicious
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                          <span className="font-mono text-xs text-brand-300 bg-brand-500/10 px-2 py-1 rounded">
                            {edge.source.slice(0, 14)}…
                          </span>
                          <ArrowRight size={14} className="text-surface-500" />
                          <span className="font-mono text-xs text-emerald-300 bg-emerald-500/10 px-2 py-1 rounded">
                            {edge.target.slice(0, 14)}…
                          </span>
                        </div>
                        {edge.risk_flags?.length > 0 && (
                          <div className="flex gap-1 mt-2 flex-wrap">
                            {edge.risk_flags.map(f => (
                              <span key={f} className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">{f}</span>
                            ))}
                          </div>
                        )}
                        <p className="text-[10px] text-surface-500 mt-2 font-mono">{edge.tx_hash}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-lg font-bold text-surface-100">${edge.amount_usd.toLocaleString()}</p>
                        <p className="text-xs text-surface-500">{edge.amount_eth.toFixed(4)} ETH</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

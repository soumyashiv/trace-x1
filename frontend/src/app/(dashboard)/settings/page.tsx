"use client";
import { useEffect, useState } from "react";
import { healthApi } from "@/lib/api";
import type { SystemHealth } from "@/types";
import Header from "@/components/layout/Header";
import { CheckCircle, XCircle, AlertTriangle, RefreshCw, Activity, Shield, Database, Zap } from "lucide-react";
import { format } from "date-fns";
import clsx from "clsx";

const statusIcon: Record<string, React.ElementType> = {
  healthy: CheckCircle, degraded: AlertTriangle, down: XCircle,
};
const statusColor: Record<string, string> = {
  healthy: "text-emerald-400", degraded: "text-amber-400", down: "text-red-400",
};

export default function SettingsPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = () => {
    setLoading(true);
    healthApi.get().then(h => { setHealth(h); setLoading(false); }).catch(() => setLoading(false));
  };

  useEffect(() => { fetchHealth(); }, []);

  return (
    <div className="min-h-screen">
      <Header
        title="Settings & System Health"
        subtitle="TRACE-X system status and configuration"
        actions={
          <button onClick={fetchHealth} className="btn-secondary flex items-center gap-1.5 text-xs">
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
        }
      />

      <div className="p-6 space-y-6">
        {/* Overall Status */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-4">
            <div className={clsx("w-14 h-14 rounded-xl flex items-center justify-center",
              health?.status === "healthy" ? "bg-emerald-500/20" : "bg-amber-500/20"
            )}>
              <Activity size={28} className={health?.status === "healthy" ? "text-emerald-400" : "text-amber-400"} />
            </div>
            <div>
              <p className="text-xs text-surface-400 uppercase tracking-widest mb-1">System Status</p>
              <h2 className="text-2xl font-bold text-surface-50 capitalize">{health?.status || "Loading…"}</h2>
              <p className="text-xs text-surface-400 mt-0.5">
                TRACE-X v{health?.version} · {health?.environment} · {health?.timestamp && format(new Date(health.timestamp), "HH:mm:ss")}
              </p>
            </div>
          </div>
        </div>

        {/* Services */}
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/5">
            <h3 className="font-semibold text-surface-100">Service Health</h3>
          </div>
          <div className="divide-y divide-white/5">
            {(health?.services || []).map(svc => {
              const Icon = statusIcon[svc.status] || AlertTriangle;
              return (
                <div key={svc.name} className="px-5 py-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Icon size={18} className={statusColor[svc.status] || "text-surface-400"} />
                    <div>
                      <p className="text-sm font-medium text-surface-200 capitalize">{svc.name.replace(/_/g, " ")}</p>
                      {svc.message && <p className="text-xs text-surface-500 mt-0.5">{svc.message}</p>}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={clsx("text-xs font-semibold capitalize", statusColor[svc.status])}>
                      {svc.status}
                    </span>
                    {svc.latency_ms !== null && (
                      <p className="text-xs text-surface-500">{svc.latency_ms}ms</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* System Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { icon: Shield, label: "Auth", value: "JWT HS256", sub: "8h expiry" },
            { icon: Database, label: "Database", value: "PostgreSQL 16", sub: "Async SQLAlchemy" },
            { icon: Zap, label: "Provider", value: "Mock Blockchain", sub: "Offline demo mode" },
          ].map(({ icon: Icon, label, value, sub }) => (
            <div key={label} className="stat-card flex items-start gap-4">
              <div className="w-10 h-10 bg-brand-500/15 rounded-lg flex items-center justify-center">
                <Icon size={18} className="text-brand-400" />
              </div>
              <div>
                <p className="text-xs text-surface-400">{label}</p>
                <p className="text-sm font-semibold text-surface-100">{value}</p>
                <p className="text-xs text-surface-500">{sub}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Disclaimer box */}
        <div className="p-5 rounded-xl bg-amber-500/5 border border-amber-500/15">
          <h3 className="text-sm font-semibold text-amber-300 mb-2">⚠ Demo Mode Limitations</h3>
          <ul className="space-y-1.5 text-xs text-surface-400">
            <li>· All blockchain data is synthetic — no real wallets or transactions are accessed</li>
            <li>· NCRP / SAHYOG integration is not active — only documented mock adapters are provided</li>
            <li>· EVM provider requires a valid ETH_RPC_URL and a transaction indexer (e.g. Etherscan API)</li>
            <li>· Risk scores and VASP attributions are probabilistic — not legal determinations</li>
            <li>· PDF reports are generated with synthetic data and carry a demo disclaimer</li>
          </ul>
        </div>

        {/* API Links */}
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-surface-200 mb-3">API Documentation</h3>
          <div className="flex gap-3 flex-wrap">
            {[
              { label: "Swagger UI", url: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs` },
              { label: "ReDoc", url: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/redoc` },
              { label: "Health Check", url: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health` },
            ].map(({ label, url }) => (
              <a key={label} href={url} target="_blank" rel="noopener noreferrer" className="btn-secondary text-xs">
                {label} ↗
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

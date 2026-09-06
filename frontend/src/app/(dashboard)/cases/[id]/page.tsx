"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { casesApi, walletsApi } from "@/lib/api";
import type { Case, Wallet } from "@/types";
import Header from "@/components/layout/Header";
import {
  GitBranch, Shield, BarChart3, Clock, Wallet as WalletIcon,
  ArrowRight, FileText, AlertTriangle, CheckCircle, TrendingUp
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import clsx from "clsx";

const riskColors: Record<string, string> = {
  low: "risk-badge-low", medium: "risk-badge-medium",
  high: "risk-badge-high", critical: "risk-badge-critical",
};

export default function CaseOverviewPage() {
  const { id } = useParams<{ id: string }>();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([casesApi.get(id), walletsApi.list(id)]).then(([c, w]) => {
      setCaseData(c); setWallets(w); setLoading(false);
    }).catch(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-10 h-10 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
    </div>
  );

  if (!caseData) return (
    <div className="min-h-screen flex items-center justify-center text-surface-400">Case not found</div>
  );

  const seedWallet = wallets.find(w => w.is_seed);
  const statusIcon = caseData.status === "closed" ? CheckCircle : caseData.status === "in_progress" ? TrendingUp : Clock;
  const StatusIcon = statusIcon;

  const navCards = [
    { href: `/cases/${id}/graph`, icon: GitBranch, label: "Transaction Graph", desc: "Interactive fund-flow visualization", color: "from-brand-900/60 to-brand-950/60 border-brand-500/20 hover:border-brand-400/40" },
    { href: `/cases/${id}/risk`, icon: Shield, label: "Risk Analysis", desc: "Explainable feature-based scoring", color: "from-red-900/30 to-red-950/40 border-red-500/20 hover:border-red-400/40" },
    { href: `/cases/${id}/vasp`, icon: BarChart3, label: "VASP Attribution", desc: "Exchange / entity identification", color: "from-amber-900/30 to-amber-950/40 border-amber-500/20 hover:border-amber-400/40" },
    { href: `/cases/${id}/timeline`, icon: Clock, label: "Timeline", desc: "Chronological transaction view", color: "from-emerald-900/30 to-emerald-950/40 border-emerald-500/20 hover:border-emerald-400/40" },
    { href: `/cases/${id}/report`, icon: FileText, label: "Generate Report", desc: "Export PDF, JSON, CSV", color: "from-purple-900/30 to-purple-950/40 border-purple-500/20 hover:border-purple-400/40" },
  ];

  return (
    <div className="min-h-screen">
      <Header
        title={caseData.case_number}
        subtitle={caseData.title}
        actions={
          <Link href={`/cases/${id}/graph`} className="btn-primary flex items-center gap-2">
            <GitBranch size={14} /> Open Graph
          </Link>
        }
      />

      <div className="p-6 space-y-6">
        {/* Case Details */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 glass-card p-5">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-surface-50">{caseData.title}</h2>
                {caseData.description && <p className="text-sm text-surface-400 mt-1">{caseData.description}</p>}
              </div>
              <span className={clsx("inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium",
                caseData.status === "in_progress" ? "text-amber-400 bg-amber-400/10 border-amber-400/30" :
                caseData.status === "closed" ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/30" :
                "text-blue-400 bg-blue-400/10 border-blue-400/30"
              )}>
                <StatusIcon size={11} />
                {caseData.status.replace("_", " ")}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              {[
                ["Victim Name", caseData.victim_name || "—"],
                ["Contact", caseData.victim_contact || "—"],
                ["Reported Amount", caseData.reported_amount_usd ? `$${caseData.reported_amount_usd.toLocaleString()}` : "—"],
                ["Opened", format(new Date(caseData.created_at), "dd MMM yyyy HH:mm")],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-surface-500 text-xs uppercase tracking-wide">{k}</p>
                  <p className="text-surface-200 font-medium mt-0.5">{v}</p>
                </div>
              ))}
            </div>
            {caseData.tags?.length > 0 && (
              <div className="flex gap-2 mt-4">
                {caseData.tags.map(t => (
                  <span key={t} className="text-xs px-2 py-0.5 rounded bg-surface-700 text-surface-300">{t}</span>
                ))}
              </div>
            )}
          </div>

          {/* Quick Stats */}
          <div className="space-y-3">
            {[
              { label: "Wallets Traced", value: caseData.wallet_count, icon: WalletIcon, color: "text-brand-400" },
              { label: "Transactions", value: caseData.transaction_count, icon: GitBranch, color: "text-emerald-400" },
              { label: "Opened", value: formatDistanceToNow(new Date(caseData.created_at), { addSuffix: true }), icon: Clock, color: "text-amber-400" },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="stat-card flex items-center gap-3">
                <Icon size={18} className={color} />
                <div>
                  <p className="text-lg font-bold text-surface-50">{value}</p>
                  <p className="text-xs text-surface-400">{label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Seed Wallet */}
        {seedWallet && (
          <div className="glass-card p-5">
            <h3 className="text-sm font-semibold text-surface-300 mb-3 flex items-center gap-2">
              <WalletIcon size={14} className="text-red-400" /> Seed Wallet (Suspect)
            </h3>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-mono text-brand-300 text-sm">{seedWallet.address}</p>
                <p className="text-xs text-surface-400 mt-0.5">{seedWallet.chain} · {seedWallet.label}</p>
              </div>
              {seedWallet.risk_score !== null && (
                <div className="text-right">
                  <p className="text-2xl font-bold text-surface-50">{seedWallet.risk_score?.toFixed(1)}</p>
                  <span className={clsx("text-xs px-2 py-0.5 rounded-full border font-medium", riskColors[seedWallet.risk_level || "low"])}>
                    {seedWallet.risk_level?.toUpperCase()}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigation Cards */}
        <div>
          <h3 className="text-sm font-semibold text-surface-300 mb-3">Investigation Tools</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
            {navCards.map(({ href, icon: Icon, label, desc, color }) => (
              <Link key={href} href={href}
                className={clsx("block p-4 rounded-xl bg-gradient-to-br border transition-all hover:-translate-y-1 group", color)}>
                <Icon size={22} className="text-surface-300 mb-3 group-hover:text-white transition-colors" />
                <p className="font-semibold text-surface-100 text-sm mb-0.5">{label}</p>
                <p className="text-xs text-surface-400">{desc}</p>
                <ArrowRight size={14} className="mt-3 text-surface-500 group-hover:text-white group-hover:translate-x-1 transition-all" />
              </Link>
            ))}
          </div>
        </div>

        {/* Wallets Table */}
        {wallets.length > 0 && (
          <div className="glass-card overflow-hidden">
            <div className="px-5 py-4 border-b border-white/5">
              <h3 className="font-semibold text-surface-100">Traced Wallets ({wallets.length})</h3>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Address</th><th>Type</th><th>Label</th>
                  <th>Risk Score</th><th>Txns</th><th>Volume</th>
                </tr>
              </thead>
              <tbody>
                {wallets.map(w => (
                  <tr key={w.id}>
                    <td><span className="font-mono text-xs text-brand-300">{w.address.slice(0, 20)}…</span></td>
                    <td><span className="text-xs text-surface-300">{w.wallet_type}</span></td>
                    <td><span className="text-xs text-surface-400">{w.label || "—"}</span></td>
                    <td>
                      {w.risk_score !== null ? (
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-surface-100">{w.risk_score.toFixed(1)}</span>
                          <span className={clsx("text-[10px] px-1.5 py-0.5 rounded-full border font-medium", riskColors[w.risk_level || "low"])}>
                            {w.risk_level?.toUpperCase()}
                          </span>
                        </div>
                      ) : <span className="text-surface-500 text-xs">Not analyzed</span>}
                    </td>
                    <td><span className="text-sm text-surface-300">{w.transaction_count}</span></td>
                    <td><span className="text-sm font-mono text-surface-300">${w.total_sent_usd.toFixed(0)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

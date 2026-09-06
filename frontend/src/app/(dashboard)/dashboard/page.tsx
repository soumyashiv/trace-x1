"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { casesApi } from "@/lib/api";
import type { Case } from "@/types";
import Header from "@/components/layout/Header";
import {
  FolderOpen, Plus, TrendingUp, AlertTriangle,
  CheckCircle, Clock, ArrowRight, Zap
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import clsx from "clsx";

const statusColors: Record<string, string> = {
  open: "text-blue-400 bg-blue-400/10 border-blue-400/30",
  in_progress: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  closed: "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
  archived: "text-surface-400 bg-surface-400/10 border-surface-400/30",
};

const statusIcons: Record<string, React.ElementType> = {
  open: Clock,
  in_progress: TrendingUp,
  closed: CheckCircle,
  archived: FolderOpen,
};

export default function DashboardPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    casesApi.list({ page_size: 20 }).then(r => {
      setCases(r.items);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const stats = {
    total: cases.length,
    open: cases.filter(c => c.status === "open").length,
    inProgress: cases.filter(c => c.status === "in_progress").length,
    closed: cases.filter(c => c.status === "closed").length,
    totalAmount: cases.reduce((s, c) => s + (c.reported_amount_usd || 0), 0),
  };

  return (
    <div className="min-h-screen">
      <Header
        title="Investigation Dashboard"
        subtitle="TRACE-X — Cryptocurrency Fraud Intelligence Platform"
        actions={
          <Link href="/cases/new" className="btn-primary flex items-center gap-2">
            <Plus size={15} />
            New Case
          </Link>
        }
      />

      <div className="p-6 space-y-6">
        {/* Stats Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Total Cases", value: stats.total, icon: FolderOpen, color: "text-brand-400", bg: "bg-brand-500/10" },
            { label: "In Progress", value: stats.inProgress, icon: TrendingUp, color: "text-amber-400", bg: "bg-amber-500/10" },
            { label: "Resolved", value: stats.closed, icon: CheckCircle, color: "text-emerald-400", bg: "bg-emerald-500/10" },
            { label: "Total Reported (USD)", value: `$${stats.totalAmount.toLocaleString()}`, icon: AlertTriangle, color: "text-red-400", bg: "bg-red-500/10" },
          ].map(({ label, value, icon: Icon, color, bg }) => (
            <div key={label} className="stat-card flex items-center gap-4">
              <div className={clsx("w-11 h-11 rounded-xl flex items-center justify-center", bg)}>
                <Icon size={20} className={color} />
              </div>
              <div>
                <p className="text-2xl font-bold text-surface-50">{value}</p>
                <p className="text-xs text-surface-400">{label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Quick Action Banner */}
        <div className="relative overflow-hidden rounded-xl p-6 bg-gradient-to-r from-brand-900/60 via-brand-800/40 to-brand-950/60 border border-brand-500/20">
          <div className="absolute right-0 top-0 w-64 h-64 bg-brand-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
          <div className="relative flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Zap size={16} className="text-brand-400" />
                <span className="text-xs font-semibold text-brand-400 uppercase tracking-wide">Quick Start</span>
              </div>
              <h2 className="text-xl font-bold text-surface-50 mb-1">Start a New Investigation</h2>
              <p className="text-sm text-surface-400">Enter a suspect wallet address to automatically trace transactions, build a graph, and generate risk intelligence.</p>
            </div>
            <Link href="/cases/new" className="btn-primary shrink-0 flex items-center gap-2">
              <Plus size={15} /> Create Case
            </Link>
          </div>
        </div>

        {/* Cases Table */}
        <div className="glass-card overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
            <h2 className="font-semibold text-surface-100">Recent Investigations</h2>
            <Link href="/cases" className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
              View all <ArrowRight size={12} />
            </Link>
          </div>

          {loading ? (
            <div className="p-8 flex justify-center">
              <div className="w-8 h-8 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
            </div>
          ) : cases.length === 0 ? (
            <div className="p-12 text-center">
              <FolderOpen size={40} className="mx-auto text-surface-600 mb-3" />
              <p className="text-surface-400">No cases yet.</p>
              <Link href="/cases/new" className="btn-primary mt-4 inline-flex items-center gap-2">
                <Plus size={14} /> Create First Case
              </Link>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Case No.</th>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Victim</th>
                  <th>Amount (USD)</th>
                  <th>Wallets</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {cases.map(c => {
                  const StatusIcon = statusIcons[c.status] || Clock;
                  return (
                    <tr key={c.id}>
                      <td>
                        <span className="font-mono text-xs text-brand-400">{c.case_number}</span>
                      </td>
                      <td>
                        <p className="font-medium text-surface-100">{c.title}</p>
                        {c.tags?.length > 0 && (
                          <div className="flex gap-1 mt-1">
                            {c.tags.slice(0, 3).map(t => (
                              <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-700 text-surface-400">{t}</span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={clsx("inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium", statusColors[c.status])}>
                          <StatusIcon size={11} />
                          {c.status.replace("_", " ")}
                        </span>
                      </td>
                      <td><span className="text-surface-300 text-sm">{c.victim_name || "—"}</span></td>
                      <td>
                        <span className="text-sm font-mono text-surface-200">
                          {c.reported_amount_usd ? `$${c.reported_amount_usd.toLocaleString()}` : "—"}
                        </span>
                      </td>
                      <td><span className="text-surface-300 text-sm">{c.wallet_count}</span></td>
                      <td>
                        <span className="text-xs text-surface-500">
                          {formatDistanceToNow(new Date(c.created_at), { addSuffix: true })}
                        </span>
                      </td>
                      <td>
                        <Link href={`/cases/${c.id}`}
                          className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
                          Investigate <ArrowRight size={12} />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

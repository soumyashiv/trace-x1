"use client";
import { useEffect, useState } from "react";
import { casesApi } from "@/lib/api";
import type { Case } from "@/types";
import Header from "@/components/layout/Header";
import Link from "next/link";
import { FolderOpen, Plus, TrendingUp, Clock, CheckCircle, Archive, ArrowRight } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import clsx from "clsx";

const statusColors: Record<string, string> = {
  open: "text-blue-400 bg-blue-400/10 border-blue-400/30",
  in_progress: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  closed: "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
  archived: "text-surface-400 bg-surface-400/10 border-surface-400/30",
};

export default function CasesListPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    casesApi.list({ page_size: 50 }).then(r => { setCases(r.items); setLoading(false); });
  }, []);

  const filtered = cases.filter(c =>
    c.title.toLowerCase().includes(filter.toLowerCase()) ||
    c.case_number.toLowerCase().includes(filter.toLowerCase()) ||
    (c.victim_name || "").toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="min-h-screen">
      <Header
        title="All Investigations"
        subtitle={`${cases.length} total cases`}
        actions={
          <Link href="/cases/new" className="btn-primary flex items-center gap-2">
            <Plus size={14} /> New Case
          </Link>
        }
      />
      <div className="p-6 space-y-4">
        <input
          className="input-field max-w-sm"
          placeholder="Search by title, case number, victim…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
        />

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-10 h-10 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <FolderOpen size={40} className="mx-auto text-surface-600 mb-3" />
            <p className="text-surface-400 mb-4">No cases found.</p>
            <Link href="/cases/new" className="btn-primary inline-flex items-center gap-2">
              <Plus size={14} /> Create Case
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtered.map(c => (
              <Link key={c.id} href={`/cases/${c.id}`}
                className="glass-card p-5 hover:border-brand-500/30 transition-all hover:-translate-y-1 group block">
                <div className="flex items-start justify-between mb-3">
                  <span className="font-mono text-xs text-brand-400">{c.case_number}</span>
                  <span className={clsx("text-[10px] px-2 py-0.5 rounded-full border font-medium", statusColors[c.status])}>
                    {c.status.replace("_", " ")}
                  </span>
                </div>
                <h3 className="font-semibold text-surface-100 text-sm mb-1 line-clamp-2">{c.title}</h3>
                {c.victim_name && <p className="text-xs text-surface-400 mb-3">Victim: {c.victim_name}</p>}
                <div className="flex items-center justify-between text-xs text-surface-500 mt-auto">
                  <span>{c.wallet_count} wallets · {c.transaction_count} txns</span>
                  <span>{formatDistanceToNow(new Date(c.created_at), { addSuffix: true })}</span>
                </div>
                {c.reported_amount_usd && (
                  <div className="mt-2 pt-2 border-t border-white/5 text-xs text-red-400 font-semibold">
                    ${c.reported_amount_usd.toLocaleString()} reported
                  </div>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

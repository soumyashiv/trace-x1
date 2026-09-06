"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { vaspApi, walletsApi } from "@/lib/api";
import type { VaspAttribution, Wallet } from "@/types";
import Header from "@/components/layout/Header";
import { Building2, CheckCircle, XCircle, AlertTriangle, Info, HelpCircle } from "lucide-react";
import { format } from "date-fns";
import clsx from "clsx";
import toast from "react-hot-toast";

export default function VaspPage() {
  const { id } = useParams<{ id: string }>();
  const [vasp, setVasp] = useState<VaspAttribution | null>(null);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    walletsApi.list(id).then(async ws => {
      const seed = ws.find(w => w.is_seed) || ws[0];
      if (!seed) return;
      setWallet(seed);
      const v = await vaspApi.attribute(id, seed.address).catch(() => null);
      setVasp(v);
    }).catch(() => toast.error("Failed to load VASP attribution")).finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-10 h-10 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
    </div>
  );

  const confPct = vasp ? Math.round(vasp.confidence * 100) : 0;
  const confColor = confPct >= 80 ? "#10b981" : confPct >= 50 ? "#f59e0b" : "#ef4444";

  return (
    <div className="min-h-screen">
      <Header title="VASP Attribution" subtitle={`Wallet: ${wallet?.address?.slice(0, 24)}…`} />

      <div className="p-6 space-y-6">
        {/* Disclaimer */}
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-3">
          <AlertTriangle size={16} className="text-amber-400 mt-0.5 shrink-0" />
          <p className="text-xs text-amber-300 leading-relaxed">
            {vasp?.disclaimer || "VASP attributions are probabilistic hypotheses. Independent legal corroboration is required before any action."}
          </p>
        </div>

        {!vasp ? (
          <div className="glass-card p-8 text-center">
            <Building2 size={40} className="mx-auto text-surface-600 mb-3" />
            <p className="text-surface-400">No VASP attribution available.</p>
          </div>
        ) : (
          <>
            {/* Entity Card */}
            <div className="glass-card p-6 relative overflow-hidden">
              <div className="absolute right-0 top-0 w-48 h-48 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"
                style={{ background: `${confColor}22` }} />
              <div className="relative flex flex-col md:flex-row items-start gap-6">
                <div className="flex-1">
                  <p className="text-xs text-surface-500 uppercase tracking-widest mb-2">Likely VASP / Entity</p>
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-12 h-12 rounded-xl bg-brand-500/20 flex items-center justify-center">
                      <Building2 size={24} className="text-brand-400" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-surface-50">
                        {vasp.likely_entity || "Unknown Entity"}
                      </h2>
                      <p className="text-sm text-surface-400 capitalize">{vasp.entity_category?.replace(/_/g, " ") || "Unidentified"}</p>
                    </div>
                  </div>
                  <div className="text-xs text-surface-500">Source: {vasp.source}</div>
                  {vasp.last_verified && (
                    <div className="text-xs text-surface-500 mt-0.5">
                      Last verified: {format(new Date(vasp.last_verified), "dd MMM yyyy")}
                    </div>
                  )}
                </div>

                {/* Confidence Gauge */}
                <div className="text-center">
                  <p className="text-xs text-surface-500 uppercase tracking-widest mb-2">Confidence</p>
                  <div className="relative w-28 h-28 mx-auto">
                    <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                      <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="12" />
                      <circle cx="50" cy="50" r="40" fill="none" stroke={confColor} strokeWidth="12"
                        strokeDasharray={`${2 * Math.PI * 40}`}
                        strokeDashoffset={`${2 * Math.PI * 40 * (1 - vasp.confidence)}`}
                        strokeLinecap="round" />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center rotate-0">
                      <span className="text-2xl font-black text-surface-50">{confPct}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Evidence */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Supporting */}
              <div className="glass-card overflow-hidden">
                <div className="px-5 py-3.5 border-b border-white/5 flex items-center gap-2">
                  <CheckCircle size={14} className="text-emerald-400" />
                  <h3 className="font-semibold text-surface-100 text-sm">Supporting Evidence ({vasp.supporting_evidence.length})</h3>
                </div>
                <div className="p-4 space-y-3">
                  {vasp.supporting_evidence.length === 0 ? (
                    <p className="text-xs text-surface-500 p-2">No supporting evidence</p>
                  ) : vasp.supporting_evidence.map((ev, i) => (
                    <div key={i} className="p-3.5 rounded-lg bg-emerald-500/5 border border-emerald-500/15">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wide">
                          {ev.evidence_type.replace(/_/g, " ")}
                        </span>
                        <span className="text-xs font-bold text-emerald-400">
                          +{(ev.confidence_impact * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-xs text-surface-300 leading-relaxed">{ev.description}</p>
                      <p className="text-[10px] text-surface-500 mt-1.5">Source: {ev.source}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Contradicting */}
              <div className="glass-card overflow-hidden">
                <div className="px-5 py-3.5 border-b border-white/5 flex items-center gap-2">
                  <XCircle size={14} className="text-red-400" />
                  <h3 className="font-semibold text-surface-100 text-sm">Contradicting Evidence ({vasp.contradicting_evidence.length})</h3>
                </div>
                <div className="p-4 space-y-3">
                  {vasp.contradicting_evidence.length === 0 ? (
                    <p className="text-xs text-surface-500 p-2">No contradicting evidence</p>
                  ) : vasp.contradicting_evidence.map((ev, i) => (
                    <div key={i} className="p-3.5 rounded-lg bg-red-500/5 border border-red-500/15">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-semibold text-red-400 uppercase tracking-wide">
                          {ev.evidence_type.replace(/_/g, " ")}
                        </span>
                        <span className="text-xs font-bold text-red-400">
                          {(ev.confidence_impact * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-xs text-surface-300 leading-relaxed">{ev.description}</p>
                      <p className="text-[10px] text-surface-500 mt-1.5">Source: {ev.source}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Alternative Hypotheses */}
            {vasp.alternative_hypotheses?.length > 0 && (
              <div className="glass-card p-5">
                <h3 className="font-semibold text-surface-100 mb-3 flex items-center gap-2">
                  <HelpCircle size={14} className="text-surface-400" /> Alternative Hypotheses
                </h3>
                <div className="space-y-2">
                  {vasp.alternative_hypotheses.map((h, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-surface-800/50 border border-white/5">
                      <div className="w-8 h-8 rounded-lg bg-surface-700 flex items-center justify-center text-xs font-bold text-surface-300 shrink-0">
                        {Math.round(h.confidence * 100)}%
                      </div>
                      <div>
                        <p className="text-sm font-medium text-surface-200">{h.entity}</p>
                        <p className="text-xs text-surface-400 mt-0.5">{h.notes}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Info box */}
            <div className="p-4 rounded-xl bg-brand-500/5 border border-brand-500/15 flex items-start gap-3">
              <Info size={14} className="text-brand-400 mt-0.5 shrink-0" />
              <div className="text-xs text-surface-400 leading-relaxed">
                <strong className="text-brand-300">Next Steps:</strong> If confidence is ≥70% and supporting evidence is strong,
                initiate a legal process (court order or MLAT) targeting the identified VASP to obtain account holder KYC data.
                File an STR with FIU-IND and cross-reference with NCRP complaint data.
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

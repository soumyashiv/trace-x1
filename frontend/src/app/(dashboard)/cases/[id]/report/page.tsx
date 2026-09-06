"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { reportsApi } from "@/lib/api";
import type { Report } from "@/types";
import Header from "@/components/layout/Header";
import { FileText, Download, Clock, CheckCircle, Loader2 } from "lucide-react";
import { format } from "date-fns";
import toast from "react-hot-toast";
import clsx from "clsx";

const formatInfo = {
  pdf: { label: "PDF Report", desc: "Professional investigation report with charts and tables", icon: "📄", color: "border-red-500/20 hover:border-red-400/40 bg-red-500/5" },
  json: { label: "JSON Export", desc: "Machine-readable structured data for integration", icon: "{ }", color: "border-brand-500/20 hover:border-brand-400/40 bg-brand-500/5" },
  csv: { label: "CSV Export", desc: "Spreadsheet-compatible transaction and wallet data", icon: "📊", color: "border-emerald-500/20 hover:border-emerald-400/40 bg-emerald-500/5" },
};

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [reports, setReports] = useState<Report[]>([]);
  const [generating, setGenerating] = useState<string | null>(null);

  useEffect(() => {
    reportsApi.list(id).then(setReports).catch(() => {});
  }, [id]);

  const generate = async (format: "pdf" | "json" | "csv") => {
    setGenerating(format);
    const t = toast.loading(`Generating ${format.toUpperCase()} report…`);
    try {
      const r = await reportsApi.generate(id, format);
      setReports(prev => [r, ...prev]);
      toast.success(`${format.toUpperCase()} report generated!`, { id: t });
    } catch (err: unknown) {
      toast.error(`Failed to generate report`, { id: t });
    } finally {
      setGenerating(null);
    }
  };

  const download = (report: Report) => {
    const url = reportsApi.downloadUrl(id, report.id);
    window.open(url, "_blank");
  };

  return (
    <div className="min-h-screen">
      <Header title="Generate Report" subtitle="Export investigation findings in multiple formats" />

      <div className="p-6 space-y-6">
        {/* Format Selection */}
        <div>
          <h2 className="text-sm font-semibold text-surface-300 mb-3">Choose Export Format</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(Object.keys(formatInfo) as Array<keyof typeof formatInfo>).map(fmt => {
              const info = formatInfo[fmt];
              const isGenerating = generating === fmt;
              return (
                <button
                  key={fmt}
                  onClick={() => generate(fmt)}
                  disabled={!!generating}
                  className={clsx(
                    "p-5 rounded-xl border text-left transition-all hover:-translate-y-1 group disabled:opacity-60 disabled:cursor-not-allowed",
                    info.color
                  )}
                >
                  <div className="text-3xl mb-3">{info.icon}</div>
                  <p className="font-semibold text-surface-100 mb-1">{info.label}</p>
                  <p className="text-xs text-surface-400">{info.desc}</p>
                  <div className="mt-4 flex items-center gap-2 text-xs text-surface-400 group-hover:text-surface-200 transition">
                    {isGenerating ? (
                      <><Loader2 size={13} className="animate-spin" /> Generating…</>
                    ) : (
                      <><FileText size={13} /> Generate</>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Info */}
        <div className="p-4 rounded-xl glass-card">
          <h3 className="text-sm font-semibold text-surface-200 mb-2">Report Contents</h3>
          <ul className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-surface-400">
            {[
              "Case information & metadata",
              "Suspect wallet details",
              "Fund-flow path (all hops)",
              "Transaction summary table",
              "Risk score & feature contributions",
              "VASP attribution with evidence",
              "Investigation recommendations",
              "Uncertainty & limitation notes",
              "Report generation timestamp",
              "Legal disclaimer",
            ].map(item => (
              <li key={item} className="flex items-center gap-1.5">
                <CheckCircle size={11} className="text-emerald-400 shrink-0" /> {item}
              </li>
            ))}
          </ul>
        </div>

        {/* Past Reports */}
        {reports.length > 0 && (
          <div className="glass-card overflow-hidden">
            <div className="px-5 py-4 border-b border-white/5">
              <h3 className="font-semibold text-surface-100">Generated Reports ({reports.length})</h3>
            </div>
            <div className="divide-y divide-white/5">
              {reports.map(r => (
                <div key={r.id} className="px-5 py-4 flex items-center justify-between hover:bg-white/[0.02] transition">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-surface-700 flex items-center justify-center text-lg">
                      {formatInfo[r.format as keyof typeof formatInfo]?.icon || "📄"}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-surface-200">{formatInfo[r.format as keyof typeof formatInfo]?.label || r.format.toUpperCase()}</p>
                      <p className="text-xs text-surface-500 flex items-center gap-1 mt-0.5">
                        <Clock size={10} /> {format(new Date(r.generated_at), "dd MMM yyyy HH:mm")}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => download(r)}
                    className="btn-secondary flex items-center gap-1.5 text-xs"
                  >
                    <Download size={13} /> Download
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

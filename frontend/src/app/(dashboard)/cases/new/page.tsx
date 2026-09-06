"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { casesApi, graphApi, walletsApi } from "@/lib/api";
import Header from "@/components/layout/Header";
import toast from "react-hot-toast";
import { GitBranch, DollarSign, User, Mail, FileText, Tag, ArrowRight, Loader2 } from "lucide-react";

export default function NewCasePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    title: "",
    description: "",
    victim_name: "",
    victim_contact: "",
    reported_amount_usd: "",
    wallet_address: "",
    tags: "",
  });

  const set = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.wallet_address.trim()) {
      toast.error("A suspect wallet address is required.");
      return;
    }
    setLoading(true);
    const t = toast.loading("Creating investigation…");
    try {
      const c = await casesApi.create({
        title: form.title,
        description: form.description || undefined,
        victim_name: form.victim_name || undefined,
        victim_contact: form.victim_contact || undefined,
        reported_amount_usd: form.reported_amount_usd ? parseFloat(form.reported_amount_usd) : undefined,
        tags: form.tags.split(",").map(s => s.trim()).filter(Boolean),
      });
      toast.loading("Adding wallet…", { id: t });
      await walletsApi.add(c.id, {
        address: form.wallet_address.trim(),
        chain: "ethereum",
        wallet_type: "suspect",
        label: "Suspect Wallet",
      });
      toast.loading("Building transaction graph…", { id: t });
      await graphApi.build(c.id, form.wallet_address.trim());
      toast.success("Investigation created!", { id: t });
      router.push(`/cases/${c.id}`);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to create case";
      toast.error(msg, { id: t });
    } finally {
      setLoading(false);
    }
  };

  const useDemoWallet = () => {
    set("wallet_address", "0xsuspect000000000000000000000000000000001");
    set("title", "SIH26183 Demo: Crypto Phishing Investigation");
    set("victim_name", "Rajeev Kumar (Synthetic)");
    set("victim_contact", "demo@tracex.sih");
    set("reported_amount_usd", "7925");
    set("description", "Victim reported loss of ₹6.5 lakh via phishing. Suspect wallet identified.");
    set("tags", "demo, phishing, sih26183");
  };

  return (
    <div className="min-h-screen">
      <Header title="New Investigation" subtitle="Enter case details and the suspect wallet to begin tracing" />

      <div className="max-w-3xl mx-auto p-6">
        {/* Demo hint */}
        <div className="mb-6 p-4 rounded-xl bg-brand-900/30 border border-brand-500/20 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-brand-300">Try the Demo Case</p>
            <p className="text-xs text-surface-400 mt-0.5">Pre-fills with synthetic SIH26183 demo data</p>
          </div>
          <button onClick={useDemoWallet} className="btn-secondary text-xs flex items-center gap-1.5">
            <GitBranch size={13} /> Load Demo
          </button>
        </div>

        <form onSubmit={handleSubmit} className="glass-card p-6 space-y-6">
          <div>
            <h2 className="text-lg font-bold text-surface-50 mb-1">Case Information</h2>
            <p className="text-xs text-surface-400">Basic details for this investigation</p>
          </div>

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-1.5">
              <span className="flex items-center gap-1.5"><FileText size={14} /> Case Title <span className="text-red-400">*</span></span>
            </label>
            <input id="case-title" className="input-field" required value={form.title}
              onChange={e => set("title", e.target.value)} placeholder="e.g. Crypto phishing fraud — Nov 2024" />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-1.5">Description</label>
            <textarea id="case-desc" className="input-field min-h-[80px] resize-none" value={form.description}
              onChange={e => set("description", e.target.value)} placeholder="Brief description of the incident…" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-1.5">
                <span className="flex items-center gap-1.5"><User size={14} /> Victim Name</span>
              </label>
              <input id="victim-name" className="input-field" value={form.victim_name}
                onChange={e => set("victim_name", e.target.value)} placeholder="Full name" />
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-1.5">
                <span className="flex items-center gap-1.5"><Mail size={14} /> Victim Contact</span>
              </label>
              <input id="victim-contact" className="input-field" value={form.victim_contact}
                onChange={e => set("victim_contact", e.target.value)} placeholder="email or phone" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-1.5">
                <span className="flex items-center gap-1.5"><DollarSign size={14} /> Reported Amount (USD)</span>
              </label>
              <input id="reported-amount" className="input-field" type="number" min="0" step="0.01"
                value={form.reported_amount_usd} onChange={e => set("reported_amount_usd", e.target.value)} placeholder="0.00" />
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-1.5">
                <span className="flex items-center gap-1.5"><Tag size={14} /> Tags</span>
              </label>
              <input id="case-tags" className="input-field" value={form.tags}
                onChange={e => set("tags", e.target.value)} placeholder="phishing, defi, sih2026" />
            </div>
          </div>

          <hr className="border-white/5" />

          {/* Wallet */}
          <div>
            <h2 className="text-lg font-bold text-surface-50 mb-1">Suspect Wallet</h2>
            <p className="text-xs text-surface-400 mb-4">The victim-reported wallet address to trace</p>
            <label className="block text-sm font-medium text-surface-300 mb-1.5">
              Wallet Address <span className="text-red-400">*</span>
            </label>
            <input
              id="wallet-address"
              className="input-field font-mono text-sm"
              required
              value={form.wallet_address}
              onChange={e => set("wallet_address", e.target.value)}
              placeholder="0x… (Ethereum address)"
            />
            <p className="text-xs text-surface-500 mt-1.5">
              The system will fetch transactions, build a graph, and run risk analysis automatically.
            </p>
          </div>

          <button
            id="create-case-submit"
            type="submit"
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-base"
          >
            {loading ? (
              <><Loader2 size={18} className="animate-spin" /> Building Investigation…</>
            ) : (
              <><ArrowRight size={18} /> Create & Trace</>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

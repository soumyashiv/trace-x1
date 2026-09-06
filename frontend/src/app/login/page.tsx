"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import toast from "react-hot-toast";
import { Eye, EyeOff, Shield, Zap, GitBranch, BarChart3 } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("analyst");
  const [password, setPassword] = useState("tracex123");
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await authApi.login(username, password);
      toast.success("Welcome to TRACE-X");
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Login failed";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: GitBranch, label: "Transaction Graph", desc: "Interactive fund-flow visualization" },
    { icon: Shield, label: "Risk Scoring", desc: "Explainable feature-based analysis" },
    { icon: Zap, label: "VASP Attribution", desc: "Evidence-backed entity identification" },
    { icon: BarChart3, label: "Investigation Reports", desc: "PDF, JSON, CSV export" },
  ];

  return (
    <div className="min-h-screen animated-bg flex items-center justify-center p-4">
      {/* Background grid */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(circle at 1px 1px, rgba(99,102,241,0.08) 1px, transparent 0)",
          backgroundSize: "40px 40px",
        }}
      />

      <div className="relative z-10 w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        {/* Left — branding */}
        <div className="hidden md:block space-y-8">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-brand-500 to-brand-700 rounded-xl flex items-center justify-center shadow-brand">
                <Shield size={24} className="text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-black gradient-text tracking-tight">TRACE-X</h1>
                <p className="text-surface-400 text-xs font-mono">SIH26183</p>
              </div>
            </div>
            <p className="text-surface-300 text-lg leading-relaxed">
              Real-Time Identification of Fraud-Linked Cryptocurrency Exchanges from Victim-Reported Wallet Addresses
            </p>
          </div>

          <div className="space-y-3">
            {features.map(({ icon: Icon, label, desc }) => (
              <div key={label} className="flex items-start gap-4 p-4 glass-card hover:border-brand-500/30 transition-all">
                <div className="w-9 h-9 bg-brand-500/20 rounded-lg flex items-center justify-center shrink-0">
                  <Icon size={18} className="text-brand-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-surface-100">{label}</p>
                  <p className="text-xs text-surface-400">{desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
            <p className="text-amber-400 text-xs font-semibold mb-1">⚠ Demo Mode</p>
            <p className="text-surface-400 text-xs">
              All data is entirely synthetic. No real blockchain data is accessed.
              Demo credentials: <span className="font-mono text-brand-400">analyst / tracex123</span>
            </p>
          </div>
        </div>

        {/* Right — login form */}
        <div className="glass-card p-8 shadow-glass">
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-1 md:hidden">
              <Shield size={20} className="text-brand-400" />
              <span className="text-xl font-black gradient-text">TRACE-X</span>
            </div>
            <h2 className="text-2xl font-bold text-surface-50">Sign In</h2>
            <p className="text-surface-400 text-sm mt-1">Access your investigation workspace</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-1.5">Username</label>
              <input
                id="login-username"
                type="text"
                className="input-field"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="analyst"
                required
                autoComplete="username"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-300 mb-1.5">Password</label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPwd ? "text" : "password"}
                  className="input-field pr-10"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPwd(!showPwd)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-200 transition"
                >
                  {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 py-3"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Authenticating…
                </>
              ) : (
                <>
                  <Shield size={16} />
                  Sign In
                </>
              )}
            </button>
          </form>

          <div className="mt-6 p-4 rounded-lg bg-surface-800/50 border border-surface-700">
            <p className="text-xs text-surface-400 font-semibold mb-2 uppercase tracking-wide">Demo Credentials</p>
            <div className="space-y-1">
              {[
                ["admin", "tracex123", "System Administrator"],
                ["analyst", "tracex123", "Lead Analyst (default)"],
                ["viewer", "tracex123", "Report Viewer"],
              ].map(([u, p, role]) => (
                <button
                  key={u}
                  type="button"
                  onClick={() => { setUsername(u); setPassword(p); }}
                  className="w-full text-left text-xs p-2 rounded hover:bg-surface-700/50 transition flex justify-between items-center"
                >
                  <span className="font-mono text-brand-400">{u}</span>
                  <span className="text-surface-500">{role}</span>
                </button>
              ))}
            </div>
          </div>

          <p className="text-center text-xs text-surface-500 mt-6">
            TRACE-X v1.0 · SIH2026 Problem 26183 · Synthetic Demo
          </p>
        </div>
      </div>
    </div>
  );
}

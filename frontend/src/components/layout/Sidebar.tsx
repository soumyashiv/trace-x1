"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, FolderOpen, PlusCircle, Settings,
  Shield, LogOut, GitBranch, ChevronRight, Activity
} from "lucide-react";
import { authApi } from "@/lib/api";
import { useRouter } from "next/navigation";
import clsx from "clsx";

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/cases", icon: FolderOpen, label: "Cases" },
  { href: "/cases/new", icon: PlusCircle, label: "New Investigation" },
  { href: "/settings", icon: Settings, label: "Settings & Health" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    authApi.logout();
    router.push("/login");
  };

  return (
    <aside className="w-60 flex-shrink-0 h-screen sticky top-0 flex flex-col"
      style={{ background: "rgba(15,23,42,0.95)", borderRight: "1px solid rgba(255,255,255,0.06)" }}>
      {/* Logo */}
      <div className="p-5 border-b border-white/5">
        <Link href="/dashboard" className="flex items-center gap-3 group">
          <div className="w-9 h-9 bg-gradient-to-br from-brand-500 to-brand-700 rounded-lg flex items-center justify-center shadow-brand group-hover:shadow-lg transition-all">
            <Shield size={18} className="text-white" />
          </div>
          <div>
            <span className="text-lg font-black gradient-text tracking-tight">TRACE-X</span>
            <p className="text-[10px] text-surface-500 font-mono leading-none mt-0.5">SIH26183</p>
          </div>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <p className="text-[10px] uppercase tracking-widest text-surface-600 font-semibold px-3 py-2">Navigation</p>
        {navItems.map(({ href, icon: Icon, label }) => {
          const active = pathname === href || (href !== "/dashboard" && href !== "/cases" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={clsx("sidebar-item", active && "active")}
            >
              <Icon size={16} />
              <span>{label}</span>
              {active && <ChevronRight size={14} className="ml-auto opacity-50" />}
            </Link>
          );
        })}

        <div className="pt-4">
          <p className="text-[10px] uppercase tracking-widest text-surface-600 font-semibold px-3 py-2">Quick Links</p>
          <Link href="/cases" className="sidebar-item">
            <GitBranch size={16} />
            <span>All Investigations</span>
          </Link>
          <Link href="/settings" className="sidebar-item">
            <Activity size={16} />
            <span>System Health</span>
          </Link>
        </div>
      </nav>

      {/* Bottom */}
      <div className="p-3 border-t border-white/5 space-y-1">
        <div className="px-3 py-2">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-surface-400">Mock Provider Active</span>
          </div>
          <p className="text-[10px] text-surface-600">Offline demo mode</p>
        </div>
        <button onClick={handleLogout} className="sidebar-item w-full text-left hover:text-red-400">
          <LogOut size={16} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}

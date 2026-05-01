"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useDashboard } from "@/context/DashboardContext";
import { Button } from "@heroui/react";

const navItems = [
  { href: "/", label: "Chat", icon: "💬" },
  { href: "/finance", label: "Finance", icon: "💰" },
  { href: "/health", label: "Health", icon: "🏥" },
  { href: "/news", label: "News", icon: "📰" },
  { href: "/markets", label: "Markets", icon: "📈" },
  { href: "/profile", label: "Profile", icon: "👤" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { userName, isDarkMode, toggleDarkMode } = useDashboard();

  const handleLogout = () => {
    localStorage.clear();
    router.push("/login");
  };

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-slate-200/50 bg-white/70 backdrop-blur-xl dark:border-white/10 dark:bg-slate-950/70 hidden lg:flex">
      <div className="flex h-full flex-col p-4">
        {/* Logo */}
        <div className="mb-8 flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 dark:bg-white">
            <span className="text-xl font-bold text-white dark:text-slate-950">J</span>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-950 dark:text-white">Jarvis</h1>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-cyan-600 dark:text-cyan-400">Personal OS</p>
          </div>
        </div>

        {/* User Info */}
        <div className="mb-8 rounded-2xl bg-slate-100/50 p-4 dark:bg-white/5">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Welcome back,</p>
          <p className="text-sm font-bold text-slate-950 dark:text-white">{userName}</p>
        </div>

        {/* Nav Links */}
        <nav className="flex-1 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-all duration-200 ${
                  isActive
                    ? "bg-slate-950 text-white shadow-lg shadow-slate-950/20 dark:bg-white dark:text-slate-950"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-white/5"
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Bottom Actions */}
        <div className="pt-4 space-y-1 border-t border-slate-200/50 dark:border-white/10">
          <button
            onClick={toggleDarkMode}
            className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-slate-600 transition-all duration-200 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-white/5"
          >
            <span>{isDarkMode ? "☀️" : "🌙"}</span>
            {isDarkMode ? "Light Mode" : "Dark Mode"}
          </button>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-rose-600 transition-all duration-200 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-500/10"
          >
            <span>🚪</span>
            Logout
          </button>
        </div>
      </div>
    </aside>
  );
}

"use client";

import { useDashboard } from "@/context/DashboardContext";
import { useRouter } from "next/navigation";

export default function MobileHeader() {
  const router = useRouter();
  const { isDarkMode, toggleDarkMode, userName } = useDashboard();

  const handleLogout = () => {
    localStorage.clear();
    router.push("/login");
  };

  return (
    <div className="lg:hidden sticky top-0 z-50 flex items-center justify-between bg-white/70 px-4 py-3 backdrop-blur-xl dark:bg-slate-950/70 border-b border-slate-200/50 dark:border-white/10">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-950 dark:bg-white">
          <span className="text-sm font-bold text-white dark:text-slate-950">J</span>
        </div>
        <span className="text-sm font-bold tracking-tight">Jarvis</span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={toggleDarkMode}
          className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 transition-all active:scale-95 dark:bg-white/5"
        >
          <span className="text-sm">{isDarkMode ? "☀️" : "🌙"}</span>
        </button>
        <button
          onClick={handleLogout}
          className="flex h-9 px-3 items-center justify-center rounded-xl bg-rose-50 text-[10px] font-bold text-rose-600 transition-all active:scale-95 dark:bg-rose-500/10 dark:text-rose-400"
        >
          LOGOUT
        </button>
      </div>
    </div>
  );
}

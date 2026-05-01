"use client";

import { useDashboard } from "@/context/DashboardContext";
import { PanelCard, SectionTitle } from "@/components/dashboard/PanelCard";

export default function ProfilePage() {
  const { dashboard, sendMessage } = useDashboard();
  const memory = dashboard?.memory;

  if (!memory) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <p className="text-slate-500 animate-pulse">Loading profile data...</p>
      </div>
    );
  }

  const emojiMap: Record<string, string> = {
    personal: "👤", diet: "🥗", finance: "💰", health: "🏋️",
    preferences: "⚙️", goals: "🎯", work: "💼", other: "📝",
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1400px] mx-auto">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 dark:text-white">User Profile</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            View everything Jarvis has learned about you to personalize your experience.
          </p>
        </div>
        <button
          onClick={() => sendMessage("What do you know about me?")}
          className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-bold hover:bg-slate-50 dark:border-white/10 dark:hover:bg-white/5"
        >
          🔍 Refresh Intelligence
        </button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {Object.entries(memory.categories).length === 0 ? (
          <div className="col-span-full py-20 text-center">
            <p className="text-slate-500">Jarvis hasn't learned any facts about you yet!</p>
            <p className="text-xs mt-1">Try saying things like "I am a vegetarian" or "My birthday is in June".</p>
          </div>
        ) : (
          Object.entries(memory.categories).map(([cat, items]) => (
            <PanelCard key={cat}>
              <SectionTitle title={`${emojiMap[cat] || "📝"} ${cat}`} />
              <ul className="space-y-3">
                {items.map((item) => (
                  <li
                    key={item.key}
                    className="flex flex-col gap-1 rounded-xl bg-slate-50 px-4 py-3 dark:bg-white/5"
                  >
                    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                      {item.key.replace(/_/g, " ")}
                    </span>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900 dark:text-white">
                        {item.value}
                      </span>
                      <button 
                        onClick={() => sendMessage(`forget my ${item.key}`)}
                        className="text-xs text-rose-500 hover:underline opacity-0 group-hover:opacity-100 transition"
                      >
                        Forget
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </PanelCard>
          ))
        )}
      </div>

      <PanelCard className="mt-8 border-rose-200/50 dark:border-rose-500/20">
        <SectionTitle title="System Memory Controls" />
         <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">
           You have complete control over your data. You can ask Jarvis to forget specific facts or clear entire categories.
         </p>
         <div className="flex flex-wrap gap-3">
            <button
               onClick={() => sendMessage("forget everything you know about me")}
               className="rounded-xl bg-rose-50 px-4 py-2 text-xs font-bold text-rose-600 transition hover:bg-rose-100 dark:bg-rose-500/10 dark:text-rose-400 dark:hover:bg-rose-500/20"
            >
              Wipe System Memory
            </button>
            <button
               onClick={() => sendMessage("summarize what you know about my finances")}
               className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-bold hover:bg-slate-50 dark:border-white/10 dark:hover:bg-white/5"
            >
              Audit Finance Knowledge
            </button>
         </div>
      </PanelCard>
    </div>
  );
}

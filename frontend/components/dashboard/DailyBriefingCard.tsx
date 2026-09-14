"use client";

import { useState, useEffect } from "react";
import { useDashboard, SuggestedAction } from "@/context/DashboardContext";
import { money } from "@/lib/utils";

export function DailyBriefingCard() {
  const {
    briefing,
    isBriefingLoading,
    loadBriefing,
    sendMessage,
    isBriefingModalOpen,
    setIsBriefingModalOpen,
  } = useDashboard();

  const [isSpeaking, setIsSpeaking] = useState(false);
  const [activeSpeech, setActiveSpeech] = useState<SpeechSynthesisUtterance | null>(null);

  // Stop TTS if unmounted
  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handleToggleSpeak = () => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      setActiveSpeech(null);
      return;
    }

    const script =
      briefing?.audio_script ||
      `${briefing?.greeting || "Hello"}. ${briefing?.headline || ""}`;

    const utterance = new SpeechSynthesisUtterance(script);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    utterance.onend = () => {
      setIsSpeaking(false);
      setActiveSpeech(null);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
      setActiveSpeech(null);
    };

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
    setActiveSpeech(utterance);
  };

  const handleActionClick = (action: SuggestedAction) => {
    if (action.action_command) {
      void sendMessage(action.action_command);
      setIsBriefingModalOpen(false);
    }
  };

  if (!briefing && isBriefingLoading) {
    return (
      <div className="rounded-3xl border border-cyan-500/20 bg-gradient-to-br from-cyan-950/40 via-slate-900/60 to-slate-950/80 p-6 shadow-2xl backdrop-blur-xl animate-pulse">
        <div className="flex items-center gap-3">
          <div className="h-6 w-32 rounded-full bg-cyan-500/20" />
          <div className="h-6 w-20 rounded-full bg-slate-700/40" />
        </div>
        <div className="mt-4 h-8 w-3/4 rounded-xl bg-slate-800/50" />
        <div className="mt-2 h-4 w-1/2 rounded-lg bg-slate-800/40" />
      </div>
    );
  }

  if (!briefing) return null;

  const pace = briefing.finance_pace;
  const health = briefing.health_progress;
  const waterProgress = Math.min(
    Math.round(((health.water.today || 0) / (health.water.goal || 2500)) * 100),
    100
  );
  const calProgress = Math.min(
    Math.round(((health.calories.today || 0) / (health.calories.goal || 2000)) * 100),
    100
  );
  const proteinProgress = Math.min(
    Math.round(((health.protein.today || 0) / (health.protein.goal || 120)) * 100),
    100
  );

  const budgetWidth = pace.total_budget > 0
    ? Math.min(Math.round((pace.forecast_month_end / pace.total_budget) * 100), 100)
    : 0;

  return (
    <>
      {/* ── Main Hero Card on Home Command Center ──────────────────────── */}
      <div className="relative overflow-hidden rounded-[28px] border border-cyan-500/30 bg-gradient-to-br from-slate-900/90 via-slate-900/95 to-slate-950 p-5 sm:p-6 shadow-2xl backdrop-blur-xl">
        {/* Glow ambient background */}
        <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="pointer-events-none absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-blue-600/10 blur-3xl" />

        {/* Top bar: Badge, Date, TTS Audio button */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-full bg-gradient-to-r from-cyan-500/20 to-blue-500/20 px-3.5 py-1 text-xs font-bold tracking-wide text-cyan-300 ring-1 ring-cyan-400/30">
              <span className="h-2 w-2 animate-ping rounded-full bg-cyan-400" />
              TODAY WITH JARVIS
            </span>
            <span className="text-xs font-medium text-slate-400">{briefing.date}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleToggleSpeak}
              className={`flex items-center gap-2 rounded-xl px-3.5 py-1.5 text-xs font-semibold shadow-sm transition-all ${
                isSpeaking
                  ? "bg-rose-500/20 text-rose-300 ring-1 ring-rose-500/40 animate-pulse"
                  : "bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 ring-1 ring-cyan-500/30"
              }`}
              title="Read briefing aloud"
            >
              <span>{isSpeaking ? "⏹️ Stop" : "🔊 Read Aloud"}</span>
            </button>
            <button
              onClick={() => void loadBriefing()}
              className="rounded-xl bg-white/5 px-2.5 py-1.5 text-xs text-slate-400 hover:bg-white/10 hover:text-white transition"
              title="Refresh Briefing"
            >
              🔄
            </button>
          </div>
        </div>

        {/* Greeting & Headline */}
        <div className="mt-4">
          <h2 className="text-xl sm:text-2xl font-extrabold tracking-tight text-white">
            {briefing.greeting}
          </h2>
          <p className="mt-1.5 text-sm sm:text-base font-medium text-slate-300 leading-relaxed">
            {briefing.headline}
          </p>
        </div>

        {/* ── Key Metrics Grid (Pace, Health, Reminders) ───────────────── */}
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {/* Spending Pace Card */}
          <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4 transition hover:border-cyan-500/20 hover:bg-white/[0.05]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">Spending Pace</span>
              <span className="text-xs font-semibold text-slate-400">Day {pace.day_of_month}/{pace.total_days}</span>
            </div>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="text-lg font-bold text-white">₹{pace.daily_burn_rate.toLocaleString()}<span className="text-xs font-normal text-slate-400">/day</span></span>
              <span className="text-xs font-medium text-slate-300">Fcst: ₹{pace.forecast_month_end.toLocaleString()}</span>
            </div>
            {/* Progress bar */}
            <div className="mt-2 h-1.5 w-full rounded-full bg-slate-800">
              <div
                className={`h-1.5 rounded-full transition-all duration-500 ${
                  pace.is_over_budget_projected ? "bg-rose-500" : "bg-cyan-500"
                }`}
                style={{ width: `${Math.max(budgetWidth, 5)}%` }}
              />
            </div>
            {pace.budget_warnings.length > 0 && (
              <p className="mt-2 text-[11px] font-medium text-amber-300">
                ⚠️ {pace.budget_warnings[0].category} projected over by ₹{pace.budget_warnings[0].overage.toLocaleString()}
              </p>
            )}
          </div>

          {/* Health Progress Card */}
          <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4 transition hover:border-cyan-500/20 hover:bg-white/[0.05]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">Health & Hydration</span>
              {health.workout_streak > 0 && (
                <span className="text-xs font-semibold text-amber-400">🔥 {health.workout_streak}d streak</span>
              )}
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <div>
                <p className="text-[10px] text-slate-400">Water</p>
                <p className="text-xs font-bold text-white">{health.water.today}ml</p>
                <div className="mt-1 h-1 w-full rounded-full bg-slate-800">
                  <div className="h-1 rounded-full bg-cyan-400" style={{ width: `${waterProgress}%` }} />
                </div>
              </div>
              <div>
                <p className="text-[10px] text-slate-400">Calories</p>
                <p className="text-xs font-bold text-white">{health.calories.today || 0}</p>
                <div className="mt-1 h-1 w-full rounded-full bg-slate-800">
                  <div className="h-1 rounded-full bg-emerald-400" style={{ width: `${calProgress}%` }} />
                </div>
              </div>
              <div>
                <p className="text-[10px] text-slate-400">Protein</p>
                <p className="text-xs font-bold text-white">{health.protein.today || 0}g</p>
                <div className="mt-1 h-1 w-full rounded-full bg-slate-800">
                  <div className="h-1 rounded-full bg-purple-400" style={{ width: `${proteinProgress}%` }} />
                </div>
              </div>
            </div>
          </div>

          {/* Schedule & Market Snapshot Card */}
          <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4 transition hover:border-cyan-500/20 hover:bg-white/[0.05] sm:col-span-2 lg:col-span-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-400">Schedule & Market</span>
              {briefing.market_news.market && (
                <span className="text-xs font-semibold text-cyan-300">
                  Nifty {briefing.market_news.market.price?.toLocaleString()}
                </span>
              )}
            </div>
            <div className="mt-2 space-y-1.5">
              {briefing.schedule_alerts.reminders.length > 0 ? (
                briefing.schedule_alerts.reminders.slice(0, 2).map((rem, i) => (
                  <p key={i} className="truncate text-xs text-slate-300">
                    🔔 <span className="font-medium text-white">{rem.task}</span>
                  </p>
                ))
              ) : (
                <p className="text-xs text-slate-400">No pending reminders for today.</p>
              )}
              {briefing.market_news.news && (
                <p className="truncate text-[11px] text-slate-400">
                  📰 {briefing.market_news.news.title}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* ── Suggested Actions (1-3 Concrete Advice Chips) ───────────── */}
        {briefing.suggested_actions.length > 0 && (
          <div className="mt-5 border-t border-white/5 pt-4">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
              💡 Suggested Actions for Today
            </p>
            <div className="mt-2.5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {briefing.suggested_actions.map((act, i) => (
                <button
                  key={i}
                  onClick={() => handleActionClick(act)}
                  className="group flex flex-col items-start rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-3 text-left transition-all hover:border-cyan-400/50 hover:bg-cyan-900/30"
                >
                  <span className="text-xs font-bold text-cyan-300 group-hover:text-cyan-200">
                    → {act.title}
                  </span>
                  <span className="mt-1 text-[11px] text-slate-300 line-clamp-2">
                    {act.description}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── On-Demand Full Briefing Modal ─────────────────────────────── */}
      {isBriefingModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md animate-in fade-in duration-200"
        >
          <div className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl border border-cyan-500/30 bg-slate-900 p-6 shadow-2xl custom-scrollbar">
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🌅</span>
                <div>
                  <h3 className="text-lg font-bold text-white">Daily Briefing Overview</h3>
                  <p className="text-xs text-slate-400">{briefing.date}</p>
                </div>
              </div>
              <button
                onClick={() => setIsBriefingModalOpen(false)}
                className="rounded-full bg-white/10 p-2 text-slate-400 hover:bg-white/20 hover:text-white transition"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <div className="rounded-2xl bg-white/5 p-4">
                <h4 className="font-bold text-cyan-300">{briefing.greeting}</h4>
                <p className="mt-1 text-sm text-slate-200">{briefing.headline}</p>
              </div>

              {/* Finance details */}
              <div className="rounded-2xl border border-white/5 bg-slate-950/50 p-4 space-y-2">
                <p className="text-xs font-bold uppercase tracking-wider text-cyan-400">Finance & Budget Pace</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm">
                  <div>
                    <span className="text-xs text-slate-400">Month Spend:</span>
                    <p className="font-bold text-white">₹{pace.month_spent.toLocaleString()}</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400">Burn Rate:</span>
                    <p className="font-bold text-white">₹{pace.daily_burn_rate.toLocaleString()}/d</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400">Month-End Fcst:</span>
                    <p className="font-bold text-white">₹{pace.forecast_month_end.toLocaleString()}</p>
                  </div>
                </div>
              </div>

              {/* Health details */}
              <div className="rounded-2xl border border-white/5 bg-slate-950/50 p-4 space-y-2">
                <p className="text-xs font-bold uppercase tracking-wider text-emerald-400">Health Goal Progress</p>
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div>
                    <span className="text-xs text-slate-400">Water:</span>
                    <p className="font-bold text-white">{health.water.today} / {health.water.goal} ml</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400">Calories:</span>
                    <p className="font-bold text-white">{health.calories.today || 0} / {health.calories.goal || 2000}</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400">Protein:</span>
                    <p className="font-bold text-white">{health.protein.today || 0} / {health.protein.goal || 120} g</p>
                  </div>
                </div>
              </div>

              {/* Audio Listen */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={handleToggleSpeak}
                  className="flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 shadow-lg hover:bg-cyan-400 transition"
                >
                  {isSpeaking ? "⏹️ Stop Audio" : "🔊 Listen to Audio Briefing"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

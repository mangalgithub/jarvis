"use client";

import { useState, useEffect } from "react";
import { useDashboard, SuggestedAction } from "@/context/DashboardContext";

let CapacitorTTS: any = null;
if (typeof window !== "undefined") {
  import("@capacitor-community/text-to-speech")
    .then((mod) => { CapacitorTTS = mod.TextToSpeech; })
    .catch(() => {});
}

function isNative(): boolean {
  return (
    typeof window !== "undefined" &&
    !!(window as any).Capacitor &&
    (window as any).Capacitor.isNativePlatform?.()
  );
}

export function DailyBriefingCard({ showCard = true }: { showCard?: boolean }) {
  const {
    briefing,
    isBriefingLoading,
    loadBriefing,
    sendMessage,
    isBriefingModalOpen,
    setIsBriefingModalOpen,
  } = useDashboard();

  const [isSpeaking, setIsSpeaking] = useState(false);

  useEffect(() => {
    return () => {
      // Cleanup TTS on unmount
      if (isNative() && CapacitorTTS) {
        CapacitorTTS.stop().catch(() => {});
      } else if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handleToggleSpeak = async () => {
    const script =
      briefing?.audio_script ||
      `${briefing?.greeting || "Hello"}. ${briefing?.headline || ""}`;

    if (isSpeaking) {
      // Stop
      if (isNative() && CapacitorTTS) {
        await CapacitorTTS.stop().catch(() => {});
      } else {
        window.speechSynthesis?.cancel();
      }
      setIsSpeaking(false);
      return;
    }

    // Start
    setIsSpeaking(true);
    if (isNative() && CapacitorTTS) {
      try {
        await CapacitorTTS.speak({
          text: script,
          lang: "en-IN",
          rate: 1.0,
          pitch: 1.0,
          volume: 1.0,
          category: "ambient",
        });
      } catch (e) {
        console.error("TTS error:", e);
      } finally {
        setIsSpeaking(false);
      }
    } else if (typeof window !== "undefined" && window.speechSynthesis) {
      const utterance = new SpeechSynthesisUtterance(script);
      utterance.lang = "en-IN";
      utterance.rate = 1.0;
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    } else {
      setIsSpeaking(false);
    }
  };

  const handleActionClick = (action: SuggestedAction) => {
    if (action.action_command) {
      void sendMessage(action.action_command);
      setIsBriefingModalOpen(false);
    }
  };

  // ── Loading skeleton ──────────────────────────────────────────────────
  if (!briefing && isBriefingLoading && showCard) {
    return (
      <div className="rounded-3xl border border-cyan-500/20 bg-gradient-to-br from-cyan-950/40 via-slate-900/60 to-slate-950/80 p-5 shadow-2xl backdrop-blur-xl animate-pulse">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="h-5 w-28 rounded-full bg-cyan-500/20" />
          <div className="h-5 w-20 rounded-full bg-slate-700/40" />
        </div>
        <div className="mt-4 h-7 w-3/4 rounded-xl bg-slate-800/50" />
        <div className="mt-2 h-4 w-1/2 rounded-lg bg-slate-800/40" />
      </div>
    );
  }

  if (!briefing) return null;

  const pace = briefing.finance_pace;
  const health = briefing.health_progress;

  const waterPct  = Math.min(Math.round(((health.water.today    || 0) / (health.water.goal    || 8)) * 100), 100);
  const calPct    = Math.min(Math.round(((health.calories.today  || 0) / (health.calories.goal  || 2000)) * 100), 100);
  const proteinPct= Math.min(Math.round(((health.protein.today   || 0) / (health.protein.goal   || 120 )) * 100), 100);
  const budgetPct = pace.total_budget > 0
    ? Math.min(Math.round((pace.forecast_month_end / pace.total_budget) * 100), 100)
    : 0;

  return (
    <>
      {/* ── Hero Card ─────────────────────────────────────────────────── */}
      {showCard && <div className="relative overflow-hidden rounded-[24px] border border-cyan-500/30 bg-gradient-to-br from-slate-900/90 via-slate-900/95 to-slate-950 p-4 sm:p-6 shadow-2xl backdrop-blur-xl">
        {/* Ambient glow */}
        <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="pointer-events-none absolute -left-16 -bottom-16 h-48 w-48 rounded-full bg-blue-600/10 blur-3xl" />

        {/* ── Top bar ── */}
        <div className="flex flex-wrap items-start justify-between gap-y-2 gap-x-3">
          {/* Badge + date */}
          <div className="flex flex-wrap items-center gap-2 min-w-0">
            <span className="flex shrink-0 items-center gap-1.5 rounded-full bg-gradient-to-r from-cyan-500/20 to-blue-500/20 px-3 py-1 text-[11px] font-bold tracking-wide text-cyan-300 ring-1 ring-cyan-400/30">
              <span className="h-1.5 w-1.5 animate-ping rounded-full bg-cyan-400" />
              TODAY WITH JARVIS
            </span>
            <span className="text-[11px] font-medium text-slate-400 truncate">{briefing.date}</span>
          </div>

          {/* Action buttons */}
          <div className="flex shrink-0 items-center gap-2">
            <button
              onClick={handleToggleSpeak}
              className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-[11px] font-semibold shadow-sm transition-all ${
                isSpeaking
                  ? "bg-rose-500/20 text-rose-300 ring-1 ring-rose-500/40 animate-pulse"
                  : "bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 ring-1 ring-cyan-500/30"
              }`}
              title="Read briefing aloud"
            >
              <span>{isSpeaking ? "⏹️" : "🔊"}</span>
              <span className="hidden xs:inline">{isSpeaking ? "Stop" : "Listen"}</span>
            </button>
            <button
              onClick={() => void loadBriefing(true)}
              className="rounded-xl bg-white/5 px-2.5 py-1.5 text-xs text-slate-400 hover:bg-white/10 hover:text-white transition"
              title="Refresh Briefing (fetches fresh data)"
            >
              🔄
            </button>
          </div>
        </div>

        {/* ── Greeting & Headline ── */}
        <div className="mt-3">
          <h2 className="text-lg sm:text-xl font-extrabold tracking-tight text-white leading-snug line-clamp-2">
            {briefing.greeting}
          </h2>
          <p className="mt-1 text-xs sm:text-sm font-medium text-slate-300 leading-relaxed line-clamp-3">
            {briefing.headline}
          </p>
        </div>

        {/* ── Metrics Grid ── */}
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">

          {/* Spending Pace */}
          <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-3 sm:p-4">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">Spending</span>
              <span className="text-[10px] font-semibold text-slate-400 whitespace-nowrap">
                Day {pace.day_of_month}/{pace.total_days}
              </span>
            </div>
            <div className="mt-2 flex items-baseline justify-between gap-1 flex-wrap">
              <span className="text-base font-bold text-white">
                ₹{pace.daily_burn_rate.toLocaleString()}
                <span className="text-[10px] font-normal text-slate-400">/day</span>
              </span>
              <span className="text-[10px] font-medium text-slate-300 whitespace-nowrap">
                Fcst: ₹{pace.forecast_month_end.toLocaleString()}
              </span>
            </div>
            <div className="mt-2 h-1.5 w-full rounded-full bg-slate-800">
              <div
                className={`h-1.5 rounded-full transition-all duration-500 ${
                  pace.is_over_budget_projected ? "bg-rose-500" : "bg-cyan-500"
                }`}
                style={{ width: `${Math.max(budgetPct, 5)}%` }}
              />
            </div>
            {pace.budget_warnings.length > 0 && (
              <p className="mt-1.5 text-[10px] font-medium text-amber-300 leading-snug">
                ⚠️ {pace.budget_warnings[0].category} over by ₹{pace.budget_warnings[0].overage.toLocaleString()}
              </p>
            )}
          </div>

          {/* Health */}
          <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-3 sm:p-4">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Health</span>
              {health.workout_streak > 0 && (
                <span className="text-[10px] font-semibold text-amber-400">🔥 {health.workout_streak}d</span>
              )}
            </div>
            <div className="mt-2 grid grid-cols-3 gap-2 text-center">
              {[
                { label: "Water", value: `${health.water.today || 0} gl`, pct: waterPct, color: "bg-cyan-400" },
                { label: "Cal", value: `${health.calories.today || 0}`, pct: calPct, color: "bg-emerald-400" },
                { label: "Protein", value: `${health.protein.today || 0}g`, pct: proteinPct, color: "bg-purple-400" },
              ].map(({ label, value, pct, color }) => (
                <div key={label}>
                  <p className="text-[9px] text-slate-400">{label}</p>
                  <p className="text-[11px] font-bold text-white leading-tight">{value}</p>
                  <div className="mt-1 h-1 w-full rounded-full bg-slate-800">
                    <div className={`h-1 rounded-full ${color}`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Schedule & Market */}
          <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-3 sm:p-4">
            <div className="flex items-center justify-between gap-1 flex-wrap">
              <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400">Schedule</span>
              {briefing.market_news.market && (
                <span className="text-[10px] font-semibold text-cyan-300 whitespace-nowrap">
                  Nifty {briefing.market_news.market.price?.toLocaleString()}
                </span>
              )}
            </div>
            <div className="mt-2 space-y-1.5">
              {briefing.schedule_alerts.reminders.length > 0 ? (
                briefing.schedule_alerts.reminders.slice(0, 2).map((rem, i) => (
                  <p key={i} className="text-[11px] text-slate-300 line-clamp-1">
                    🔔 <span className="font-medium text-white">{rem.task}</span>
                  </p>
                ))
              ) : (
                <p className="text-[11px] text-slate-400">No pending reminders.</p>
              )}
              {briefing.market_news.news && (
                <p className="text-[10px] text-slate-400 line-clamp-2">
                  📰 {briefing.market_news.news.title}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* ── Suggested Actions ── */}
        {briefing.suggested_actions.length > 0 && (
          <div className="mt-4 border-t border-white/5 pt-3">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              💡 Suggested Actions
            </p>
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
              {briefing.suggested_actions.map((act, i) => (
                <button
                  key={i}
                  onClick={() => handleActionClick(act)}
                  className="group flex flex-col items-start rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-3 text-left transition-all hover:border-cyan-400/50 hover:bg-cyan-900/30 active:scale-[0.98]"
                >
                  <span className="text-[11px] font-bold text-cyan-300 group-hover:text-cyan-200 leading-snug">
                    → {act.title}
                  </span>
                  <span className="mt-1 text-[10px] text-slate-300 line-clamp-2 leading-snug">
                    {act.description}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── Cache indicator ── */}
        <p className="mt-3 text-[9px] text-slate-600 text-right">
          Cached for today · tap 🔄 to refresh
        </p>
      </div>}

      {/* ── Full Briefing Modal ─────────────────────────────────────────── */}
      {isBriefingModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-950/80 backdrop-blur-md"
          onClick={(e) => { if (e.target === e.currentTarget) setIsBriefingModalOpen(false); }}
        >
          <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-t-3xl sm:rounded-3xl border border-cyan-500/30 bg-slate-900 p-5 sm:p-6 shadow-2xl custom-scrollbar">
            {/* Modal header */}
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xl shrink-0">🌅</span>
                <div className="min-w-0">
                  <h3 className="text-base font-bold text-white truncate">Daily Briefing</h3>
                  <p className="text-[10px] text-slate-400">{briefing.date}</p>
                </div>
              </div>
              <button
                onClick={() => setIsBriefingModalOpen(false)}
                className="shrink-0 rounded-full bg-white/10 p-2 text-slate-400 hover:bg-white/20 hover:text-white transition"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-4">
              {/* Greeting */}
              <div className="rounded-2xl bg-white/5 p-4">
                <h4 className="font-bold text-cyan-300 text-sm">{briefing.greeting}</h4>
                <p className="mt-1 text-xs text-slate-200 leading-relaxed">{briefing.headline}</p>
              </div>

              {/* Finance */}
              <div className="rounded-2xl border border-white/5 bg-slate-950/50 p-4">
                <p className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 mb-3">Finance & Budget</p>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  {[
                    { label: "Month Spend", val: `₹${pace.month_spent.toLocaleString()}` },
                    { label: "Burn Rate", val: `₹${pace.daily_burn_rate.toLocaleString()}/d` },
                    { label: "Month-End Forecast", val: `₹${pace.forecast_month_end.toLocaleString()}` },
                    { label: "Budget", val: pace.total_budget > 0 ? `₹${pace.total_budget.toLocaleString()}` : "Not set" },
                  ].map(({ label, val }) => (
                    <div key={label}>
                      <span className="text-[10px] text-slate-400">{label}</span>
                      <p className="font-bold text-white">{val}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Health */}
              <div className="rounded-2xl border border-white/5 bg-slate-950/50 p-4">
                <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 mb-3">Health Goals</p>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  {[
                    { label: "Water", val: `${health.water.today || 0} / ${health.water.goal || 8} glasses`, pct: waterPct, color: "bg-cyan-400" },
                    { label: "Calories", val: `${health.calories.today || 0} / ${health.calories.goal || 2000}`, pct: calPct, color: "bg-emerald-400" },
                    { label: "Protein", val: `${health.protein.today || 0} / ${health.protein.goal || 120}g`, pct: proteinPct, color: "bg-purple-400" },
                  ].map(({ label, val, pct, color }) => (
                    <div key={label}>
                      <span className="text-[10px] text-slate-400">{label}</span>
                      <p className="font-bold text-white leading-tight">{val}</p>
                      <div className="mt-1.5 h-1 w-full rounded-full bg-slate-800">
                        <div className={`h-1 rounded-full ${color}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Suggested Actions in Modal */}
              {briefing.suggested_actions.length > 0 && (
                <div className="space-y-2">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">💡 Actions</p>
                  {briefing.suggested_actions.map((act, i) => (
                    <button
                      key={i}
                      onClick={() => handleActionClick(act)}
                      className="group w-full flex flex-col items-start rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-3 text-left transition-all hover:border-cyan-400/50 hover:bg-cyan-900/30"
                    >
                      <span className="text-xs font-bold text-cyan-300">→ {act.title}</span>
                      <span className="mt-0.5 text-[11px] text-slate-300">{act.description}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Audio button */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={handleToggleSpeak}
                  className="flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 shadow-lg hover:bg-cyan-400 transition active:scale-95"
                >
                  {isSpeaking ? "⏹️ Stop Audio" : "🔊 Listen to Briefing"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

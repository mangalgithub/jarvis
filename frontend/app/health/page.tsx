"use client";

import { useDashboard } from "@/context/DashboardContext";
import { PanelCard } from "@/components/dashboard/PanelCard";
import { AnalyticsChart } from "@/components/dashboard/AnalyticsChart";
import { timeAgo } from "@/lib/utils";

export default function HealthPage() {
  const { dashboard, sendMessage } = useDashboard();
  const health = dashboard?.health;

  if (!health) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <p className="text-slate-500 animate-pulse">Loading health data...</p>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1400px] mx-auto">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 dark:text-white">Health & Fitness</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Track your nutrition, hydration, and activity.
          </p>
        </div>
        <button
          onClick={() => sendMessage("Health summary")}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold shadow-sm transition-all hover:bg-slate-50 dark:border-white/10 dark:bg-white/10 dark:text-white"
        >
          📊 Daily Summary
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <PanelCard className="p-2">
          <AnalyticsChart 
            title="7-Day Calorie Intake" 
            data={health.trends} 
            dataKey="calories" 
            color="#f97316" 
          />
        </PanelCard>
        <PanelCard className="p-2">
          <AnalyticsChart 
            title="7-Day Protein Intake (g)" 
            data={health.trends} 
            dataKey="protein" 
            color="#8b5cf6" 
          />
        </PanelCard>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Hydration */}
        <PanelCard title="💧 Hydration">
          <HealthBar
            label="Water Intake"
            today={health.water.today}
            goal={health.water.goal}
            unit=" gl"
            color="bg-sky-500"
          />
          <div className="mt-6 grid grid-cols-2 gap-2">
            <button
              onClick={() => sendMessage("Drank 1 glass of water")}
              className="rounded-xl bg-sky-50 py-3 text-xs font-bold text-sky-600 dark:bg-sky-500/10 dark:text-sky-400"
            >
              +1 Glass
            </button>
            <button
              onClick={() => sendMessage("Drank 2 glasses of water")}
              className="rounded-xl bg-sky-50 py-3 text-xs font-bold text-sky-600 dark:bg-sky-500/10 dark:text-sky-400"
            >
              +2 Glasses
            </button>
          </div>
        </PanelCard>

        {/* Nutrition */}
        <PanelCard title="🥗 Nutrition">
          <div className="space-y-6">
            <HealthBar
              label="Calories"
              today={health.nutrition.calories.today}
              goal={health.nutrition.calories.goal}
              unit=" kcal"
              color="bg-orange-500"
            />
            <HealthBar
              label="Protein"
              today={health.nutrition.protein.today}
              goal={health.nutrition.protein.goal}
              unit="g"
              color="bg-violet-500"
            />
          </div>
          <button
            onClick={() => sendMessage("Log my breakfast")}
            className="mt-6 w-full rounded-xl bg-slate-950 py-3 text-sm font-bold text-white dark:bg-white dark:text-slate-950"
          >
            Log Meal
          </button>
        </PanelCard>

        {/* Activity */}
        <PanelCard title="🏋️ Activity">
          <div className="rounded-2xl bg-slate-50 px-4 py-5 dark:bg-white/5 text-center">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Workout Streak</p>
            <p className="mt-2 text-4xl font-bold text-slate-950 dark:text-white">
              {health.workout.streak_days} Days
            </p>
          </div>
          
          {health.workout.last && (
            <div className="mt-6 p-4 rounded-2xl border border-slate-100 dark:border-white/5">
              <p className="text-xs font-bold text-slate-500 uppercase">Last Session</p>
              <div className="mt-2 flex justify-between items-end">
                <div>
                  <p className="text-lg font-bold capitalize">{health.workout.last.type}</p>
                  <p className="text-sm text-slate-500">{timeAgo(health.workout.last.logged_at)}</p>
                </div>
                <p className="text-2xl font-bold">{health.workout.last.duration_minutes.toFixed(0)}m</p>
              </div>
            </div>
          )}

          <button
            onClick={() => sendMessage("Did 30 min gym")}
            className="mt-6 w-full rounded-xl border border-slate-200 py-3 text-sm font-bold hover:bg-slate-50 dark:border-white/10 dark:hover:bg-white/5"
          >
            Log Workout
          </button>
        </PanelCard>
      </div>
    </div>
  );
}

function HealthBar({ label, today, goal, unit = "", color = "bg-emerald-500" }: { label: string; today: number; goal: number; unit?: string; color?: string }) {
  const pct = goal > 0 ? Math.min((today / goal) * 100, 100) : 0;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-semibold text-slate-800 dark:text-slate-200">{label}</span>
        <span className="text-slate-500 dark:text-slate-400">
          {today.toLocaleString()}{unit} / {goal.toLocaleString()}{unit}
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
        <div className={`h-full ${color} transition-all duration-500 ease-out`} style={{ width: `${Math.max(pct, 2)}%` }} />
      </div>
    </div>
  );
}

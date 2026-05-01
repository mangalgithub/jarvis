"use client";

import { useDashboard } from "@/context/DashboardContext";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { PanelCard, SectionTitle } from "@/components/dashboard/PanelCard";
import { AnalyticsChart } from "@/components/dashboard/AnalyticsChart";
import { money, shortDate } from "@/lib/utils";
import { Card } from "@heroui/react";

export default function FinancePage() {
  const { dashboard, dateRange, setDateRange, category, setCategory, loadDashboard, sendMessage } = useDashboard();
  const finance = dashboard?.finance;

  if (!finance) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <p className="text-slate-500 animate-pulse">Loading finance data...</p>
      </div>
    );
  }

  const maxCategoryTotal = Math.max(
    ...(finance.categoryBreakdown.map((item) => item.total) || [0]),
    1
  );

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 dark:text-white">Finance Dashboard</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Monitor your spending, income, and financial goals.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold shadow-sm dark:border-white/10 dark:bg-white/10 dark:text-white"
          >
            {["today", "yesterday", "this week", "this month", "all time"].map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold shadow-sm dark:border-white/10 dark:bg-white/10 dark:text-white"
          >
            {["All", "Food", "Grocery", "Travel", "Shopping", "Investment", "Bills", "Health", "Entertainment", "Education", "Rent", "Other"].map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <MetricCard label="Today" value={finance.summary.todayExpenses} />
        <MetricCard label="Month Spend" value={finance.summary.monthExpenses} />
        <MetricCard label="Month Income" value={finance.summary.monthIncome} />
        <MetricCard label="Net" value={finance.summary.monthNet} />
        <MetricCard label="Recurring" value={finance.summary.recurringMonthly} />
        <MetricCard label="Filtered Total" value={finance.summary.filteredExpenses} />
      </div>

      {/* Analytics Chart */}
      <PanelCard className="p-2">
        <AnalyticsChart 
          title="7-Day Spending Trend" 
          data={finance.trends} 
          dataKey="amount" 
          color="#06b6d4" 
        />
      </PanelCard>

      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
        {/* Income vs Expense */}
        <PanelCard title="Income vs Expense">
          <div className="space-y-6">
            <ProgressRow 
              label="Income" 
              value={finance.summary.monthIncome} 
              max={Math.max(finance.summary.monthIncome, finance.summary.monthExpenses, 1)} 
              valueText={money(finance.summary.monthIncome)}
              tone="success"
            />
            <ProgressRow 
              label="Expense" 
              value={finance.summary.monthExpenses} 
              max={Math.max(finance.summary.monthIncome, finance.summary.monthExpenses, 1)} 
              valueText={money(finance.summary.monthExpenses)}
              tone="danger"
            />
            <div className="rounded-2xl bg-slate-100 p-4 dark:bg-white/5">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Net Balance</p>
              <p className={`mt-1 text-2xl font-bold ${finance.summary.monthNet >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                {money(finance.summary.monthNet)}
              </p>
            </div>
          </div>
        </PanelCard>

        {/* Category Breakdown */}
        <PanelCard title="Category Spend" subtitle={dateRange}>
          <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
            {finance.categoryBreakdown.length === 0 ? (
              <p className="text-sm text-slate-500">No expenses in this period.</p>
            ) : (
              finance.categoryBreakdown.map((item) => (
                <ProgressRow 
                  key={item.category}
                  label={item.category}
                  value={item.total}
                  max={maxCategoryTotal}
                  valueText={money(item.total)}
                />
              ))
            )}
          </div>
        </PanelCard>

        {/* Budgets */}
        <PanelCard title="Budgets">
          <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
            {finance.budgets.length === 0 ? (
              <p className="text-sm text-slate-500">No budgets set yet.</p>
            ) : (
              finance.budgets.map((b) => (
                <ProgressRow 
                  key={b.category}
                  label={b.category}
                  value={b.spent}
                  max={b.budget}
                  valueText={`${money(b.spent)} / ${money(b.budget)}`}
                  tone={b.progress > 90 ? "danger" : "default"}
                />
              ))
            )}
          </div>
        </PanelCard>

        {/* Savings Goals */}
        <PanelCard title="Savings Goals" className="xl:col-span-2">
          <div className="grid gap-4 sm:grid-cols-2">
            {finance.savingsGoals.length === 0 ? (
              <p className="text-sm text-slate-500">No savings goals yet.</p>
            ) : (
              finance.savingsGoals.map((goal) => {
                const progress = goal.target_amount > 0 ? ((goal.saved_amount || 0) / goal.target_amount) * 100 : 0;
                return (
                  <div key={goal._id} className="rounded-2xl border border-slate-200 p-4 dark:border-white/10 dark:bg-white/5">
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <p className="font-bold text-slate-950 dark:text-white">{goal.name}</p>
                      <span className="text-xs font-semibold text-emerald-500">{progress.toFixed(0)}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700">
                      <div className="h-2 rounded-full bg-emerald-500 transition-all duration-300" style={{ width: `${progress}%` }} />
                    </div>
                    <div className="mt-2 flex justify-between text-xs text-slate-500">
                      <span>{money(goal.saved_amount)}</span>
                      <span>Target: {money(goal.target_amount)}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </PanelCard>

        {/* Recent Expenses */}
        <PanelCard title="Recent Expenses" className="xl:col-span-1">
          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
            {finance.recentExpenses.length === 0 ? (
              <p className="text-sm text-slate-500">No recent expenses.</p>
            ) : (
              finance.recentExpenses.map((exp) => (
                <div key={exp._id} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 p-3 dark:bg-white/5">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-slate-900 dark:text-white">{exp.description}</p>
                    <p className="text-[10px] text-slate-500">{exp.category} | {shortDate(exp.occurred_at || exp.created_at)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-slate-900 dark:text-white">{money(exp.amount)}</p>
                    <div className="mt-1 flex gap-2">
                      <button 
                        onClick={() => sendMessage(`delete expense id ${exp._id}`)}
                        className="text-[10px] text-rose-500 hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </PanelCard>
      </div>
    </div>
  );
}

function ProgressRow({ label, valueText, value, max, tone = "default" }: { label: string; valueText: string; value: number; max: number; tone?: "default" | "danger" | "success" }) {
  const width = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const barClassName = tone === "danger" ? "bg-rose-500" : tone === "success" ? "bg-emerald-500" : "bg-cyan-600";

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-slate-800 dark:text-slate-200">{label}</span>
        <span className="text-slate-600 dark:text-slate-400">{valueText}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700">
        <div className={`h-2 rounded-full ${barClassName} transition-all duration-300`} style={{ width: `${Math.max(width, 3)}%` }} />
      </div>
    </div>
  );
}

"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@heroui/react";

type Message = {
  role: "user" | "assistant";
  content: string;
  actions?: AgentAction[];
};

type AgentAction = {
  type: string;
  [key: string]: unknown;
};

type ChatResponse = {
  reply: string;
  actions: AgentAction[];
};

type FinanceSummary = {
  todayExpenses: number;
  monthExpenses: number;
  filteredExpenses: number;
  monthIncome: number;
  monthNet: number;
  recurringMonthly: number;
};

type CategoryTotal = {
  category: string;
  total: number;
};

type BudgetStatus = {
  category: string;
  budget: number;
  spent: number;
  remaining: number;
  period: string;
  progress: number;
};

type Expense = {
  _id: string;
  amount: number;
  description: string;
  category: string;
  payment_method?: string;
  occurred_at?: string;
  created_at?: string;
};

type SavingsGoal = {
  _id: string;
  name: string;
  target_amount: number;
  saved_amount?: number;
  target_date?: string;
};

type RecurringExpense = {
  _id: string;
  description: string;
  amount: number;
  category: string;
  frequency?: string;
};

type NewsArticle = {
  title: string;
  description?: string;
  url: string;
  source?: string;
  published_at?: string;
  image_url?: string;
};

type NewsCategory = {
  label: string;
  articles: NewsArticle[];
};

type HealthData = {
  water: { today: number; goal: number; progress: number };
  nutrition: {
    calories: { today: number; goal: number };
    protein: { today: number; goal: number };
  };
  workout: {
    streak_days: number;
    last: { type: string; duration_minutes: number; logged_at: string } | null;
  };
} | null;

type MemoryData = {
  total: number;
  categories: Record<string, { key: string; value: string }[]>;
} | null;

type StockIndex = {
  name: string;
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
};

type StockData = {
  indices: StockIndex[];
} | null;

type Reminder = {
  _id: string;
  task: string;
  execute_at: string;
  status: string;
};

type DashboardResponse = {
  finance: {
    summary: FinanceSummary;
    categoryBreakdown: CategoryTotal[];
    budgets: BudgetStatus[];
    recentExpenses: Expense[];
    savingsGoals: SavingsGoal[];
    recurringExpenses: RecurringExpense[];
  } | null;
  news: Record<string, NewsCategory> | null;
  health: HealthData;
  memory: MemoryData;
  stocks: StockData;
  reminders: Reminder[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:3000";

const starterPrompts = [
  "I spent 250 on lunch by UPI",
  "Set food budget 5000 per month",
  "Drank 2 glasses of water",
  "Remember I am vegetarian",
  "Nifty 50 today",
  "Reliance stock price",
  "Roadmap to learn Python",
  "Best machine learning courses",
  "Remind me to drink water in 1 hour",
  "Remind me to check emails at 5pm",
  "Top gainers today",
  "Latest India news",
  "AI news summary",
  "Health summary",
];

const dateRangeOptions = [
  "today",
  "yesterday",
  "this week",
  "this month",
  "all time",
];

const categoryOptions = [
  "All",
  "Food",
  "Grocery",
  "Travel",
  "Shopping",
  "Investment",
  "Bills",
  "Health",
  "Entertainment",
  "Education",
  "Rent",
  "Other",
];

function money(amount = 0) {
  return `Rs ${amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function shortDate(value?: string) {
  if (!value) return "Today";
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
  }).format(new Date(value));
}

function useDarkMode() {
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    const isDark = saved === "dark";
    setDark(isDark);
    document.documentElement.classList.toggle("dark", isDark);
    setMounted(true);
  }, []);

  const toggle = () => {
    setDark((current) => {
      const next = !current;
      document.documentElement.classList.toggle("dark", next);
      localStorage.setItem("theme", next ? "dark" : "light");
      return next;
    });
  };

  return { dark, toggle, mounted };
}

function SectionTitle({
  title,
  subtitle,
  right,
}: {
  title: string;
  subtitle?: string;
  right?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div>
        <h2 className="text-lg font-semibold tracking-tight text-slate-950 dark:text-white sm:text-xl">
          {title}
        </h2>
        {subtitle ? (
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            {subtitle}
          </p>
        ) : null}
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </div>
  );
}

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: number | undefined;
}) {
  return (
    <Card className="group relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/90 p-4 shadow-[0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_rgba(15,23,42,0.12)] dark:border-white/10 dark:bg-white/5 dark:shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-cyan-500 via-sky-500 to-indigo-500 opacity-70" />
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
        {money(value)}
      </p>
    </Card>
  );
}

function ProgressRow({
  label,
  valueText,
  value,
  max,
  tone = "default",
}: {
  label: string;
  valueText: string;
  value: number;
  max: number;
  tone?: "default" | "danger" | "success";
}) {
  const width = max > 0 ? Math.min((value / max) * 100, 100) : 0;

  const barClassName =
    tone === "danger"
      ? "bg-rose-500"
      : tone === "success"
        ? "bg-emerald-500"
        : "bg-cyan-600";

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-slate-800 dark:text-slate-200">
          {label}
        </span>
        <span className="text-slate-600 dark:text-slate-400">{valueText}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700">
        <div
          className={`h-2 rounded-full ${barClassName} transition-all duration-300`}
          style={{ width: `${Math.max(width, 3)}%` }}
        />
      </div>
    </div>
  );
}

function PanelCard({
  title,
  children,
  className = "",
  right,
}: {
  title: string;
  children: ReactNode;
  className?: string;
  right?: ReactNode;
}) {
  return (
    <Card
      className={`group relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_rgba(15,23,42,0.12)] dark:border-white/10 dark:bg-white/5 dark:shadow-[0_10px_30px_rgba(0,0,0,0.35)] ${className}`}
    >
      <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-cyan-500 via-sky-500 to-indigo-500 opacity-60" />
      <SectionTitle title={title} right={right} />
      {children}
    </Card>
  );
}

function timeAgo(isoString?: string): string {
  if (!isoString) return "";
  const diff = Date.now() - new Date(isoString).getTime();
  const hours = Math.floor(diff / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function HealthBar({
  label,
  today,
  goal,
  unit = "",
  color = "bg-emerald-500",
}: {
  label: string;
  today: number;
  goal: number;
  unit?: string;
  color?: string;
}) {
  const pct = goal > 0 ? Math.min((today / goal) * 100, 100) : 0;
  const over = today > goal;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-slate-800 dark:text-slate-200">{label}</span>
        <span className="text-slate-500 dark:text-slate-400">
          {today.toLocaleString()}{unit} / {goal.toLocaleString()}{unit}
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${over ? "bg-rose-500" : color}`}
          style={{ width: `${Math.max(pct, 3)}%` }}
        />
      </div>
    </div>
  );
}

function MemoryWidget({
  memory,
  onAsk,
}: {
  memory: MemoryData;
  onAsk: (msg: string) => void;
}) {
  if (!memory || memory.total === 0) {
    return (
      <PanelCard title="What Jarvis Knows">
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-400">
          I don't know much about you yet! Tell me your preferences so I can help you better.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            onClick={() => onAsk("Remember I am vegetarian")}
            className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/20"
          >
            "Remember I am vegetarian"
          </button>
          <button
            onClick={() => onAsk("My monthly salary is 50000")}
            className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/20"
          >
            "My monthly salary is 50000"
          </button>
        </div>
      </PanelCard>
    );
  }

  const emojiMap: Record<string, string> = {
    personal: "👤", diet: "🥗", finance: "💰", health: "🏋️",
    preferences: "⚙️", goals: "🎯", work: "💼", other: "📝",
  };

  return (
    <PanelCard title={`User Profile (${memory.total} facts)`}>
      <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
        {Object.entries(memory.categories).map(([cat, items]) => (
          <div key={cat}>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              {emojiMap[cat] || "📝"} {cat}
            </h4>
            <ul className="space-y-1">
              {items.map((item) => (
                <li
                  key={item.key}
                  className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-white/5"
                >
                  <span className="font-medium capitalize text-slate-700 dark:text-slate-300">
                    {item.key.replace(/_/g, " ")}
                  </span>
                  <span className="text-right font-semibold text-slate-900 dark:text-white">
                    {item.value}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          onClick={() => onAsk("What do you know about me?")}
          className="rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-600 transition-colors hover:bg-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-400 dark:hover:bg-indigo-500/20"
        >
          View All
        </button>
        <button
          onClick={() => onAsk("Forget my diet")}
          className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200 dark:bg-white/10 dark:text-slate-400 dark:hover:bg-white/20"
        >
          Forget...
        </button>
      </div>
    </PanelCard>
  );
}

function StockWidget({
  stocks,
  onAsk,
}: {
  stocks: StockData;
  onAsk: (msg: string) => void;
}) {
  if (!stocks || stocks.indices.length === 0) {
    return (
      <PanelCard title="Markets">
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-400">
          Market data loading...
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            onClick={() => onAsk("Nifty 50 today")}
            className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/20"
          >
            Nifty 50
          </button>
          <button
            onClick={() => onAsk("Top gainers today")}
            className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/20"
          >
            Top Gainers
          </button>
        </div>
      </PanelCard>
    );
  }

  return (
    <PanelCard title="Markets">
      <div className="space-y-2">
        {stocks.indices.map((idx) => {
          const isPositive = idx.change_pct >= 0;
          return (
            <div
              key={idx.name}
              className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2.5 dark:bg-white/5"
            >
              <div>
                <p className="text-sm font-semibold text-slate-800 dark:text-white">{idx.name}</p>
                <p className="text-xs text-slate-500">{idx.price?.toLocaleString("en-IN")}</p>
              </div>
              <div className={`text-right text-xs font-bold ${isPositive ? "text-emerald-500" : "text-red-500"}`}>
                <p>{isPositive ? "▲" : "▼"} {Math.abs(idx.change_pct ?? 0).toFixed(2)}%</p>
                <p className="font-normal opacity-75">
                  {isPositive ? "+" : ""}{(idx.change ?? 0).toFixed(2)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          onClick={() => onAsk("Reliance stock price")}
          className="rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-600 transition-colors hover:bg-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-400 dark:hover:bg-indigo-500/20"
        >
          Reliance
        </button>
        <button
          onClick={() => onAsk("Top gainers today")}
          className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-600 transition-colors hover:bg-emerald-100 dark:bg-emerald-500/10 dark:text-emerald-400 dark:hover:bg-emerald-500/20"
        >
          Gainers 📈
        </button>
        <button
          onClick={() => onAsk("Axis bluechip mutual fund NAV")}
          className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200 dark:bg-white/10 dark:text-slate-400 dark:hover:bg-white/20"
        >
          MF NAV
        </button>
      </div>
    </PanelCard>
  );
}

function HealthWidget({
  health,
  onAsk,
}: {
  health: HealthData;
  onAsk: (msg: string) => void;
}) {
  return (
    <Card className="group relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_rgba(15,23,42,0.12)] dark:border-white/10 dark:bg-white/5 dark:shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
      <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-400 opacity-70" />

      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold tracking-tight text-slate-950 dark:text-white">
          Health
        </h2>
        <button
          type="button"
          onClick={() => onAsk("Health summary")}
          className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md dark:border-white/10 dark:bg-white/10 dark:text-slate-300"
        >
          📊 Summary
        </button>
      </div>

      {health === null || health === undefined ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Log water, workouts, or meals to see your health data here.
        </p>
      ) : (
        <div className="space-y-4">
          {/* Water */}
          <HealthBar
            label="💧 Water"
            today={health.water.today}
            goal={health.water.goal}
            unit=" gl"
            color="bg-sky-500"
          />

          {/* Calories */}
          <HealthBar
            label="🔥 Calories"
            today={health.nutrition.calories.today}
            goal={health.nutrition.calories.goal}
            unit=" kcal"
            color="bg-orange-500"
          />

          {/* Protein */}
          <HealthBar
            label="🥩 Protein"
            today={health.nutrition.protein.today}
            goal={health.nutrition.protein.goal}
            unit="g"
            color="bg-violet-500"
          />

          {/* Workout streak */}
          <div className="rounded-2xl bg-slate-50 px-4 py-3 dark:bg-white/5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Workout Streak
                </p>
                <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-white">
                  🏋️ {health.workout.streak_days} day{health.workout.streak_days !== 1 ? "s" : ""}
                </p>
              </div>
              {health.workout.last && (
                <div className="text-right text-xs text-slate-500 dark:text-slate-400">
                  <p className="font-medium capitalize">{health.workout.last.type}</p>
                  <p>{health.workout.last.duration_minutes?.toFixed(0)} min</p>
                  <p>{timeAgo(health.workout.last.logged_at)}</p>
                </div>
              )}
            </div>
          </div>

          {/* Quick log buttons */}
          <div className="flex flex-wrap gap-2 pt-1">
            {["Drank 2 glasses of water", "Did 30 min gym", "Ate 500 calories 30g protein"].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => onAsk(p)}
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md dark:border-white/10 dark:bg-white/10 dark:text-slate-300"
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

const NEWS_TABS = [
  { key: "india", label: "🇮🇳 India" },

  { key: "world", label: "🌍 World" },
  { key: "ai", label: "🤖 AI" },
];

function NewsPanel({
  news,
  onAsk,
}: {
  news: Record<string, { label: string; articles: { title: string; description?: string; url: string; source?: string; published_at?: string; image_url?: string }[] }> | null;
  onAsk: (message: string) => void;
}) {
  const [activeTab, setActiveTab] = useState<string>("india");

  const categoryData = news?.[activeTab];
  const articles = categoryData?.articles ?? [];

  return (
    <Card className="group relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_rgba(15,23,42,0.12)] dark:border-white/10 dark:bg-white/5 dark:shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
      <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-rose-500 via-orange-400 to-amber-400 opacity-70" />

      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold tracking-tight text-slate-950 dark:text-white">
          News
        </h2>
        <button
          type="button"
          onClick={() => onAsk("Morning briefing")}
          className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-md dark:border-white/10 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/15"
        >
          📰 Daily briefing
        </button>
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-1 rounded-2xl bg-slate-100 p-1 dark:bg-white/5">
        {NEWS_TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 rounded-xl py-2 text-xs font-semibold transition-all duration-200 ${
              activeTab === tab.key
                ? "bg-white text-slate-950 shadow-sm dark:bg-white/15 dark:text-white"
                : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Articles */}
      <div className="space-y-3">
        {news === null ? (
          <p className="text-sm leading-6 text-slate-500 dark:text-slate-400">
            Loading news…
          </p>
        ) : articles.length === 0 ? (
          <p className="text-sm leading-6 text-slate-500 dark:text-slate-400">
            No headlines available. Try asking Jarvis: &quot;Latest India news&quot;
          </p>
        ) : (
          articles.map((article, index) => (
            <div
              key={`${activeTab}-${index}`}
              className="group/article rounded-2xl border border-slate-200 bg-slate-50 p-3 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md dark:border-white/10 dark:bg-white/5"
            >
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block"
              >
                <p className="text-sm font-medium leading-5 text-slate-900 transition-colors group-hover/article:text-cyan-700 dark:text-slate-100 dark:group-hover/article:text-cyan-400">
                  {article.title}
                </p>
                <div className="mt-1.5 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                  {article.source && (
                    <span className="rounded-full bg-slate-200 px-2 py-0.5 font-medium dark:bg-white/10">
                      {article.source}
                    </span>
                  )}
                  {article.published_at && (
                    <span>{timeAgo(article.published_at)}</span>
                  )}
                </div>
              </a>
              <button
                type="button"
                onClick={() =>
                  onAsk(`Summarize this news: ${article.title}`)
                }
                className="mt-2 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 dark:border-white/10 dark:bg-white/10 dark:text-slate-300"
              >
                Ask Jarvis
              </button>
            </div>
          ))
        )}
      </div>

      {articles.length > 0 && (
        <button
          type="button"
          onClick={() =>
            onAsk(`${NEWS_TABS.find((t) => t.key === activeTab)?.label ?? ""} news summary`)
          }
          className="mt-4 w-full rounded-2xl border border-slate-200 bg-white py-2 text-xs font-semibold text-slate-700 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-md dark:border-white/10 dark:bg-white/10 dark:text-white dark:hover:bg-white/15"
        >
          Summarize {categoryData?.label ?? ""} News
        </button>
      )}
    </Card>
  );
}

export default function Home() {
  const router = useRouter();
  const { dark, toggle, mounted } = useDarkMode();
  const [userName, setUserName] = useState("User");

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Jarvis is online. Log expenses, check budgets, get the latest news, and ask for a morning briefing.",
    },
  ]);

  const [input, setInput] = useState("");
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [liveReminders, setLiveReminders] = useState<Reminder[]>([]);
  const [dateRange, setDateRange] = useState("this month");
  const [category, setCategory] = useState("All");
  const [isSending, setIsSending] = useState(false);
  const [isDashboardLoading, setIsDashboardLoading] = useState(true);
  const [error, setError] = useState("");

  const finance = dashboard?.finance;

  const maxCategoryTotal = useMemo(
    () =>
      Math.max(
        ...(finance?.categoryBreakdown.map((item) => item.total) || [0]),
        1,
      ),
    [finance],
  );

  const incomeExpenseMax = Math.max(
    finance?.summary.monthIncome || 0,
    finance?.summary.monthExpenses || 0,
    1,
  );

  const loadDashboard = useCallback(async () => {
    setIsDashboardLoading(true);

    try {
      const token = localStorage.getItem("jarvis_token");
      if (!token) {
        router.push("/login");
        return;
      }
      setUserName(localStorage.getItem("jarvis_name") || "User");

      const searchParams = new URLSearchParams({
        userId: "default-user",
        dateRange,
      });

      if (category !== "All") {
        searchParams.set("category", category);
      }

      const response = await fetch(
        `${API_BASE_URL}/api/dashboard?${searchParams}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.status === 401) {
        localStorage.clear();
        router.push("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const data = await response.json() as DashboardResponse;
      setDashboard(data);
      if (data.reminders) {
        setLiveReminders(data.reminders);
      }
    } catch {
      setError(
        "Jarvis could not load dashboard data. Make sure backend, agents, and MongoDB are running.",
      );
    } finally {
      setIsDashboardLoading(false);
    }
  }, [category, dateRange]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    const token = localStorage.getItem("jarvis_token");
    if (!token) return;
    const wsUrl = API_BASE_URL.replace(/^http/, "ws") + `/api/ws/default-user?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "reminder_triggered") {
          setLiveReminders((prev) => {
            const updated = [...prev];
            const existingIdx = updated.findIndex((r) => r._id === message.reminder._id);
            if (existingIdx >= 0) {
              updated[existingIdx] = message.reminder;
            } else {
              updated.push(message.reminder);
            }
            return updated;
          });
          // Show browser notification if permitted
          if (Notification.permission === "granted") {
            new Notification("Jarvis Reminder", {
              body: message.reminder.task,
            });
          } else if (Notification.permission !== "denied") {
            Notification.requestPermission().then(permission => {
              if (permission === "granted") {
                new Notification("Jarvis Reminder", {
                  body: message.reminder.task,
                });
              }
            });
          }
        }
      } catch (err) {
        console.error("WebSocket message parsing error:", err);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  async function sendMessage(message: string) {
    const trimmedMessage = message.trim();

    if (!trimmedMessage || isSending) {
      return;
    }

    setInput("");
    setError("");
    setIsSending(true);
    setMessages((currentMessages) => [
      ...currentMessages,
      { role: "user", content: trimmedMessage },
    ]);

    try {
      const token = localStorage.getItem("jarvis_token");
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          userId: "default-user",
          message: trimmedMessage,
        }),
      });

      if (response.status === 401) {
        localStorage.clear();
        router.push("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const data = (await response.json()) as ChatResponse;

      setMessages((currentMessages) => [
        ...currentMessages,
        { role: "assistant", content: data.reply, actions: data.actions || [] },
      ]);
      setActions(data.actions || []);
      void loadDashboard();
    } catch {
      setError(
        "Jarvis could not reach the backend. Make sure Node is running on port 3000 and Python agents are running on port 8000.",
      );
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(input);
  }

  function requestDeleteExpense(expense: Expense) {
    void sendMessage(`delete expense id ${expense._id}`);
  }

  function requestEditExpense(expense: Expense) {
    const amount = window.prompt("New amount", String(expense.amount));

    if (!amount) {
      return;
    }

    void sendMessage(`update expense id ${expense._id} amount to ${amount}`);
  }

  function acknowledgeReminder(reminder: Reminder) {
    const token = localStorage.getItem("jarvis_token");
    // Send acknowledge to backend
    fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ userId: "default-user", message: `acknowledge reminder ${reminder._id}` }),
    }).catch(console.error);

    setLiveReminders(prev => prev.filter(r => r._id !== reminder._id));
  }

  if (!mounted) {
    return <main className="min-h-screen bg-slate-100 dark:bg-slate-950" />;
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.14),_transparent_35%),linear-gradient(to_bottom_right,_#f8fafc,_#f8fafc,_#ecfeff)] text-slate-950 transition-colors duration-300 dark:bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.16),_transparent_35%),linear-gradient(to_bottom_right,_#0f172a,_#020617,_#020617)] dark:text-white">
      <div className="mx-auto w-full max-w-[1600px] px-4 py-4 sm:px-6 lg:px-8">
        <div className="mb-5 overflow-hidden rounded-[32px] border border-slate-200/80 bg-white/90 shadow-[0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur dark:border-white/10 dark:bg-white/5 dark:shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
          <div className="flex flex-col gap-4 border-b border-slate-200/70 p-5 md:flex-row md:items-end md:justify-between dark:border-white/10">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-700 dark:text-cyan-300">
                Personal OS
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <h1 className="text-3xl font-semibold tracking-tight text-slate-950 dark:text-white sm:text-4xl">
                  Jarvis
                </h1>
                <button
                  type="button"
                  onClick={toggle}
                  className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-md dark:border-white/10 dark:bg-white/10 dark:text-white dark:hover:bg-white/15"
                >
                  {dark ? "☀️ Light" : "🌙 Dark"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    localStorage.clear();
                    router.push("/login");
                  }}
                  className="rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-semibold text-rose-700 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-rose-100 hover:shadow-md dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-100 dark:hover:bg-rose-500/15"
                >
                  Logout
                </button>
              </div>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-400">
                Finance command center with chat, budgets, income, recurring
                expenses, and savings goals.
              </p>
            </div>

            <div className="flex flex-wrap gap-3 text-xs text-slate-600 dark:text-slate-300">
              <span className="rounded-full border border-slate-200 bg-white px-3 py-2 shadow-sm dark:border-white/10 dark:bg-white/10">
                Backend: localhost:3000
              </span>
              <span className="rounded-full border border-slate-200 bg-white px-3 py-2 shadow-sm dark:border-white/10 dark:bg-white/10">
                Agents: localhost:8000
              </span>
            </div>
          </div>
        </div>

        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <MetricCard label="Today" value={finance?.summary.todayExpenses} />
            <MetricCard label="Month Spend" value={finance?.summary.monthExpenses} />
            <MetricCard label="Month Income" value={finance?.summary.monthIncome} />
            <MetricCard label="Net" value={finance?.summary.monthNet} />
            <MetricCard label="Recurring" value={finance?.summary.recurringMonthly} />
          </div>

          {error ? (
            <Card className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 shadow-sm dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-100">
              {error}
            </Card>
          ) : null}

          <Card className="rounded-3xl border border-slate-200/80 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur dark:border-white/10 dark:bg-white/5 dark:shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
            <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
              <label className="grid gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Date
                </span>
                <select
                  className="min-h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 text-sm text-slate-950 shadow-sm outline-none transition-all duration-200 focus:-translate-y-0.5 focus:border-cyan-500 focus:shadow-md dark:border-white/10 dark:bg-slate-950 dark:text-white"
                  onChange={(event) => setDateRange(event.target.value)}
                  value={dateRange}
                >
                  {dateRangeOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>

              <label className="grid gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Category
                </span>
                <select
                  className="min-h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 text-sm text-slate-950 shadow-sm outline-none transition-all duration-200 focus:-translate-y-0.5 focus:border-cyan-500 focus:shadow-md dark:border-white/10 dark:bg-slate-950 dark:text-white"
                  onChange={(event) => setCategory(event.target.value)}
                  value={category}
                >
                  {categoryOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>

              <Card className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 shadow-none dark:border-white/10 dark:bg-white/5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Filtered
                </p>
                <p className="mt-1 text-base font-semibold text-slate-950 dark:text-white">
                  {money(finance?.summary.filteredExpenses)}
                </p>
              </Card>
            </div>
          </Card>

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,0.9fr)]">
            <section className="grid min-w-0 gap-5">
              <div className="grid gap-5 lg:grid-cols-3">
                <PanelCard title="Income vs Expense">
                  <div className="space-y-4">
                    <ProgressRow
                      label="Income"
                      valueText={money(finance?.summary.monthIncome)}
                      value={finance?.summary.monthIncome || 0}
                      max={incomeExpenseMax}
                      tone="success"
                    />
                    <ProgressRow
                      label="Expense"
                      valueText={money(finance?.summary.monthExpenses)}
                      value={finance?.summary.monthExpenses || 0}
                      max={incomeExpenseMax}
                      tone="danger"
                    />
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 dark:bg-white/5">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                        Net
                      </p>
                      <p className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">
                        {money(finance?.summary.monthNet)}
                      </p>
                    </div>
                  </div>
                </PanelCard>

                <PanelCard
                  title="Category Spend"
                  right={
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {isDashboardLoading ? "Updating..." : "This month"}
                    </span>
                  }
                >
                  <div className="space-y-4">
                    {finance?.categoryBreakdown.length ? (
                      finance.categoryBreakdown.map((item) => (
                        <ProgressRow
                          key={item.category}
                          label={item.category}
                          valueText={money(item.total)}
                          value={item.total}
                          max={maxCategoryTotal}
                        />
                      ))
                    ) : (
                      <p className="text-sm leading-6 text-slate-600 dark:text-slate-400">
                        No category spending yet.
                      </p>
                    )}
                  </div>
                </PanelCard>

                <PanelCard title="Budgets">
                  <div className="space-y-5">
                    {finance?.budgets.length ? (
                      finance.budgets.map((budget) => {
                        const overBudget = budget.progress > 100;
                        const nearLimit = budget.progress >= 80 && !overBudget;

                        return (
                          <div key={`${budget.category}-${budget.period}`}>
                            <div className="mb-2 flex items-center justify-between gap-3 text-sm">
                              <span className="font-medium text-slate-800 dark:text-slate-200">
                                {budget.category}
                              </span>
                              <span className="text-slate-600 dark:text-slate-400">
                                {money(budget.spent)} / {money(budget.budget)}
                              </span>
                            </div>

                            <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700">
                              <div
                                className={`h-2 rounded-full transition-all duration-300 ${
                                  overBudget ? "bg-rose-500" : "bg-emerald-500"
                                }`}
                                style={{
                                  width: `${Math.min(Math.max(budget.progress, 3), 100)}%`,
                                }}
                              />
                            </div>

                            <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
                              Remaining {money(budget.remaining)}
                            </p>

                            {overBudget ? (
                              <div className="mt-2 rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-100">
                                Over budget
                              </div>
                            ) : nearLimit ? (
                              <div className="mt-2 rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-100">
                                Near limit
                              </div>
                            ) : null}
                          </div>
                        );
                      })
                    ) : (
                      <p className="text-sm leading-6 text-slate-600 dark:text-slate-400">
                        No budgets set yet.
                      </p>
                    )}
                  </div>
                </PanelCard>
              </div>

              <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.95fr)]">
                <PanelCard title="Chat" className="flex min-h-[720px] flex-col">
                  <div className="flex-1 overflow-y-auto pr-1">
                    <div className="space-y-4">
                      {messages.map((message, index) => (
                        <div
                          key={`${message.role}-${index}`}
                          className={`flex ${
                            message.role === "user"
                              ? "justify-end"
                              : "justify-start"
                          }`}
                        >
                          <Card
                            className={`max-w-[92%] rounded-3xl px-4 py-3 shadow-sm transition-all duration-200 hover:-translate-y-0.5 sm:max-w-[78%] ${
                              message.role === "user"
                                ? "border border-cyan-700/20 bg-gradient-to-br from-cyan-600 to-sky-600 text-white"
                                : "border border-slate-200 bg-slate-50 text-slate-950 dark:border-white/10 dark:bg-white/5 dark:text-white"
                            }`}
                          >
                            <p className="whitespace-pre-wrap break-words text-sm leading-6">
                              {message.content}
                            </p>

                            {/* Render Video Tiles for Learning Agent Actions */}
                            {message.actions?.map((action, i) => {
                              if (
                                action.type === "learning_videos" ||
                                action.type === "learning_channel" ||
                                action.type === "learning_roadmap" ||
                                action.type === "learning_playlists" ||
                                action.type === "learning_courses"
                              ) {
                                // Extract videos or playlists depending on the action type
                                const items = (action.videos as any[]) || 
                                              (action.playlists as any[]) || 
                                              (action.starter_videos as any[]) || [];
                                
                                // For learning_courses, we might have both
                                const moreItems = (action.playlists && action.videos) 
                                  ? [...(action.playlists as any[]), ...(action.videos as any[])]
                                  : items;

                                if (!moreItems.length) return null;

                                return (
                                  <div key={i} className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                                    {moreItems.map((v: any, vIdx: number) => (
                                      <a
                                        key={vIdx}
                                        href={v.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="group block overflow-hidden rounded-xl border border-slate-200/60 bg-white/50 transition-all hover:-translate-y-0.5 hover:shadow-md dark:border-white/10 dark:bg-black/20"
                                      >
                                        <div className="aspect-video w-full overflow-hidden bg-slate-100 dark:bg-slate-800">
                                          {v.thumbnail && (
                                            <img
                                              src={v.thumbnail}
                                              alt={v.title}
                                              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                                            />
                                          )}
                                        </div>
                                        <div className="p-3">
                                          <h4 className="line-clamp-2 text-xs font-semibold leading-snug text-slate-800 dark:text-slate-200">
                                            {v.title}
                                          </h4>
                                          <p className="mt-1 text-[10px] font-medium text-slate-500 dark:text-slate-400">
                                            {v.channel}
                                          </p>
                                        </div>
                                      </a>
                                    ))}
                                  </div>
                                );
                              }
                              return null;
                            })}
                          </Card>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mt-5 border-t border-slate-200 pt-4 dark:border-white/10">
                    <div className="mb-4 flex flex-wrap gap-2">
                      {starterPrompts.map((prompt) => (
                        <button
                          key={prompt}
                          type="button"
                          onClick={() => void sendMessage(prompt)}
                          className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-700 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-md dark:border-white/10 dark:bg-white/10 dark:text-white dark:hover:bg-white/15"
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>

                    <form
                      onSubmit={handleSubmit}
                      className="flex flex-col gap-3 sm:flex-row sm:items-center"
                    >
                      <input
                        aria-label="Tell Jarvis what to do"
                        className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-950 shadow-sm outline-none transition-all duration-200 placeholder:text-slate-400 focus:-translate-y-0.5 focus:border-cyan-500 focus:shadow-md dark:border-white/10 dark:bg-slate-950 dark:text-white dark:placeholder:text-slate-500"
                        placeholder="Tell Jarvis what to do..."
                        value={input}
                        onChange={(event) => setInput(event.target.value)}
                      />
                      {/* <button
                        type="submit"
                        disabled={isSending}
                        className="shrink-0 rounded-2xl bg-slate-950 px-5 py-3 text-sm font-semibold text-black shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-800 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60 dark:bg-red dark:text-slate-950 dark:hover:bg-slate-200"
                      >
                        {isSending ? "Sending" : "Send"}
                      </button> */}

          <button
  type="submit"
  disabled={isSending}
  className="shrink-0 rounded-2xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-blue-700 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60 dark:bg-blue-500 dark:hover:bg-blue-600"
>
  {isSending ? "Sending" : "Send"}
</button>
                    </form>
                  </div>
                </PanelCard>

                <PanelCard title="Recent Expenses" className="min-h-[720px]">
                  <div className="space-y-4">
                    {finance?.recentExpenses.length ? (
                      finance.recentExpenses.map((expense) => (
                        <div
                          key={expense._id}
                          className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md dark:border-white/10 dark:bg-white/5"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold text-slate-950 dark:text-white">
                                {expense.description}
                              </p>
                              <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                                {expense.category} |{" "}
                                {expense.payment_method || "unknown"} |{" "}
                                {shortDate(
                                  expense.occurred_at || expense.created_at,
                                )}
                              </p>
                            </div>
                            <p className="shrink-0 text-sm font-semibold text-slate-800 dark:text-slate-200">
                              {money(expense.amount)}
                            </p>
                          </div>

                          <div className="mt-4 flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() => requestEditExpense(expense)}
                              className="rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-md dark:border-white/10 dark:bg-white/10 dark:text-white dark:hover:bg-white/15"
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              onClick={() => requestDeleteExpense(expense)}
                              className="rounded-full border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-rose-100 hover:shadow-md dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-100 dark:hover:bg-rose-500/15"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm leading-6 text-slate-600 dark:text-slate-400">
                        No expenses logged yet.
                      </p>
                    )}
                  </div>
                </PanelCard>
              </div>
            </section>

            <aside className="grid gap-5">
              <PanelCard title="Savings Goals">
                <div className="space-y-4">
                  {finance?.savingsGoals.length ? (
                    finance.savingsGoals.map((goal) => {
                      const saved = goal.saved_amount || 0;
                      const progress = goal.target_amount
                        ? Math.min((saved / goal.target_amount) * 100, 100)
                        : 0;

                      return (
                        <div key={goal._id}>
                          <div className="mb-2 flex justify-between gap-3 text-sm">
                            <span className="font-medium text-slate-800 dark:text-slate-200">
                              {goal.name}
                            </span>
                            <span className="text-slate-600 dark:text-slate-400">
                              {money(saved)} / {money(goal.target_amount)}
                            </span>
                          </div>
                          <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700">
                            <div
                              className="h-2 rounded-full bg-amber-500 transition-all duration-300"
                              style={{ width: `${Math.max(progress, 3)}%` }}
                            />
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-sm leading-6 text-slate-600 dark:text-slate-400">
                      No savings goals yet.
                    </p>
                  )}
                </div>
              </PanelCard>

              <PanelCard title="Recurring">
                <div className="space-y-3">
                  {finance?.recurringExpenses.length ? (
                    finance.recurringExpenses.map((item) => (
                      <div
                        key={item._id}
                        className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md dark:border-white/10 dark:bg-white/5"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-slate-950 dark:text-white">
                              {item.description}
                            </p>
                            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                              {item.category} | {item.frequency || "monthly"}
                            </p>
                          </div>
                          <p className="shrink-0 text-sm font-semibold text-slate-800 dark:text-slate-200">
                            {money(item.amount)}
                          </p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm leading-6 text-slate-600 dark:text-slate-400">
                      No recurring expenses yet.
                    </p>
                  )}
                </div>
              </PanelCard>

              {liveReminders.length > 0 && (
                <PanelCard title="Reminders">
                  <div className="space-y-3">
                    {liveReminders.map(r => {
                      const triggered = r.status === "triggered";
                      return (
                        <div key={r._id} className={`rounded-xl border p-3 ${triggered ? 'border-red-200 bg-red-50 dark:border-red-900/30 dark:bg-red-900/10' : 'border-slate-200 bg-slate-50 dark:border-white/10 dark:bg-white/5'}`}>
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className={`text-sm font-semibold ${triggered ? 'text-red-700 dark:text-red-400' : 'text-slate-800 dark:text-slate-200'}`}>
                                {triggered && "🔔 "} {r.task}
                              </p>
                              <p className="mt-1 text-xs text-slate-500">
                                {new Date(r.execute_at).toLocaleString(undefined, {
                                  month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
                                })}
                              </p>
                            </div>
                            {triggered && (
                              <button
                                onClick={() => acknowledgeReminder(r)}
                                className="shrink-0 rounded-full bg-red-100 px-3 py-1.5 text-xs font-semibold text-red-700 transition-colors hover:bg-red-200 dark:bg-red-500/20 dark:text-red-300 dark:hover:bg-red-500/30"
                              >
                                Dismiss
                              </button>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </PanelCard>
              )}

              <HealthWidget health={dashboard?.health ?? null} onAsk={sendMessage} />

              <StockWidget stocks={dashboard?.stocks ?? null} onAsk={sendMessage} />

              <MemoryWidget memory={dashboard?.memory ?? null} onAsk={sendMessage} />

              <NewsPanel news={dashboard?.news ?? null} onAsk={sendMessage} />

              <PanelCard title="Agent Actions">
                <div className="space-y-3">
                  {actions.filter(
                    (a) =>
                      !["news_fetched", "news_briefing", "news_fetch_failed"].includes(a.type)
                  ).length ? (
                    actions
                      .filter(
                        (a) =>
                          !["news_fetched", "news_briefing", "news_fetch_failed"].includes(a.type)
                      )
                      .map((action, index) => (
                        <Card
                          key={`${action.type}-${index}`}
                          className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-none transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md dark:border-white/10 dark:bg-white/5"
                        >
                          <p className="text-sm font-semibold text-slate-950 dark:text-white">
                            {action.type}
                          </p>
                          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs leading-5 text-slate-600 dark:text-slate-300">
                            {JSON.stringify(action, null, 2)}
                          </pre>
                        </Card>
                      ))
                  ) : (
                    <p className="text-sm leading-6 text-slate-600 dark:text-slate-400">
                      Agent results will appear here after Jarvis handles a
                      command.
                    </p>
                  )}
                </div>
              </PanelCard>
            </aside>
          </div>
        </div>
      </div>
    </main>
  );
}
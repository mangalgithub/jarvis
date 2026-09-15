  "use client";

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useSmsExpenseTracker } from "@/hooks/useSmsExpenseTracker";
import { API_BASE_URL } from "@/lib/apiConfig";

// Types
export type Message = {
  role: "user" | "assistant";
  content: string;
  image?: string;
  actions?: AgentAction[];
};

export type AgentAction = {
  type: string;
  [key: string]: unknown;
};

export type ChatResponse = {
  reply: string;
  actions: AgentAction[];
};

export type FinanceSummary = {
  todayExpenses: number;
  monthExpenses: number;
  filteredExpenses: number;
  monthIncome: number;
  monthNet: number;
  recurringMonthly: number;
};

export type CategoryTotal = {
  category: string;
  total: number;
};

export type BudgetStatus = {
  category: string;
  budget: number;
  spent: number;
  remaining: number;
  period: string;
  progress: number;
};

export type Expense = {
  _id: string;
  amount: number;
  description: string;
  category: string;
  payment_method?: string;
  occurred_at?: string;
  created_at?: string;
  source?: "sms" | "manual" | string;
  sms_metadata?: {
    sender?: string;
    bank?: string;
    account_last4?: string;
    reference_id?: string;
  };
};

export type SavingsGoal = {
  _id: string;
  name: string;
  target_amount: number;
  saved_amount?: number;
  target_date?: string;
};

export type RecurringExpense = {
  _id: string;
  description: string;
  amount: number;
  category: string;
  frequency?: string;
};

export type NewsArticle = {
  title: string;
  description?: string;
  url: string;
  source?: string;
  published_at?: string;
  image_url?: string;
};

export type NewsCategory = {
  label: string;
  articles: NewsArticle[];
};

export type HealthData = {
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

export type MemoryData = {
  total: number;
  categories: Record<string, { key: string; value: string }[]>;
} | null;

export type StockIndex = {
  name: string;
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
};

export type StockData = {
  indices: StockIndex[];
} | null;

export type Reminder = {
  _id: string;
  task: string;
  execute_at: string;
  status: string;
};

export type DashboardResponse = {
  finance: {
    summary: FinanceSummary;
    categoryBreakdown: CategoryTotal[];
    budgets: BudgetStatus[];
    recentExpenses: Expense[];
    savingsGoals: SavingsGoal[];
    recurringExpenses: RecurringExpense[];
    trends: { date: string; amount: number }[];
  } | null;
  news: Record<string, NewsCategory> | null;
  health: (HealthData & {
    trends: { date: string; calories: number; protein: number; water: number }[];
  }) | null;
  memory: MemoryData;
  stocks: StockData;
  reminders: Reminder[];
};

export type SuggestedAction = {
  title: string;
  description: string;
  category: "finance" | "health" | "schedule" | "market" | string;
  action_command?: string;
};

export type DailyBriefingData = {
  date_key: string;
  date: string;
  greeting: string;
  headline: string;
  audio_script: string;
  suggested_actions: SuggestedAction[];
  finance_pace: {
    day_of_month: number;
    total_days: number;
    days_remaining: number;
    today_spent: number;
    month_spent: number;
    daily_burn_rate: number;
    forecast_month_end: number;
    total_budget: number;
    budget_variance: number;
    is_over_budget_projected: boolean;
    budget_warnings: Array<{
      category: string;
      budget: number;
      spent: number;
      forecast: number;
      overage: number;
    }>;
  };
  health_progress: {
    water: { today: number; goal: number; progress?: number };
    calories: { today: number; goal: number };
    protein: { today: number; goal: number };
    workout_streak: number;
  };
  schedule_alerts: {
    reminders: Array<{ _id: string; task: string; execute_at?: string }>;
    recurring_bills: Array<{ description: string; amount: number; category: string }>;
    reminders_count: number;
  };
  market_news: {
    market?: { name?: string; price?: number; change?: number; change_pct?: number } | null;
    news?: { title?: string; source?: string } | null;
  };
};

interface DashboardContextType {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  input: string;
  setInput: React.Dispatch<React.SetStateAction<string>>;
  actions: AgentAction[];
  dashboard: DashboardResponse | null;
  liveReminders: Reminder[];
  dateRange: string;
  setDateRange: React.Dispatch<React.SetStateAction<string>>;
  category: string;
  setCategory: React.Dispatch<React.SetStateAction<string>>;
  isSending: boolean;
  isDashboardLoading: boolean;
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  userName: string;
  error: string;
  setError: React.Dispatch<React.SetStateAction<string>>;
  loadDashboard: () => Promise<void>;
  sendMessage: (message: string, image?: string) => Promise<void>;
  acknowledgeReminder: (reminder: Reminder) => void;
  // SMS expense tracking
  smsExpenses: Expense[];
  smsTrackingActive: boolean;
  lastSmsExpense: { amount: number; description: string; category: string; bank: string } | null;
  // Daily Briefing
  briefing: DailyBriefingData | null;
  isBriefingLoading: boolean;
  loadBriefing: (forceRefresh?: boolean) => Promise<void>;
  isBriefingModalOpen: boolean;
  setIsBriefingModalOpen: React.Dispatch<React.SetStateAction<boolean>>;
}



const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [userName, setUserName] = useState("User");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Jarvis is online. Log expenses, check budgets, get the latest news, and ask for a morning briefing.",
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
  const [isDarkMode, setIsDarkMode] = useState(false);
  // SMS tracking state
  const [smsExpenses, setSmsExpenses] = useState<Expense[]>([]);
  const [smsTrackingActive, setSmsTrackingActive] = useState(false);
  const [lastSmsExpense, setLastSmsExpense] = useState<{ amount: number; description: string; category: string; bank: string } | null>(null);
  // Daily Briefing state
  const [briefing, setBriefing] = useState<DailyBriefingData | null>(null);
  const [isBriefingLoading, setIsBriefingLoading] = useState(false);
  const [isBriefingModalOpen, setIsBriefingModalOpen] = useState(false);

  // Initialize theme
  useEffect(() => {
    const savedTheme = localStorage.getItem("jarvis_theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initialDark = savedTheme === "dark" || (!savedTheme && prefersDark);

    setIsDarkMode(initialDark);
    if (initialDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, []);

  const toggleDarkMode = () => {
    setIsDarkMode((prev) => {
      const next = !prev;
      if (next) {
        document.documentElement.classList.add("dark");
        localStorage.setItem("jarvis_theme", "dark");
      } else {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("jarvis_theme", "light");
      }
      return next;
    });
  };

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
      setError("Jarvis could not load dashboard data. Make sure backend, agents, and MongoDB are running.");
    } finally {
      setIsDashboardLoading(false);
    }
  }, [category, dateRange, router]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  // ── Fetch SMS-tracked expenses from backend ──────────────────────────────
  const loadSmsExpenses = useCallback(async () => {
    const token = localStorage.getItem("jarvis_token");
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/expenses/sms?limit=20`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json() as { expenses: Expense[]; count: number };
      const rawList = data.expenses || [];
      const seenRefs = new Set<string>();
      const seenSigs = new Set<string>();
      const deduplicated: Expense[] = [];

      for (const exp of rawList) {
        const ref = exp.sms_metadata?.reference_id?.trim();
        const dateStr = (exp.occurred_at || exp.created_at || "").slice(0, 10);
        const sig = `${exp.amount}-${(exp.description || "").trim().toLowerCase()}-${dateStr}`;

        if (ref) {
          if (seenRefs.has(ref)) continue;
          seenRefs.add(ref);
        } else if (seenSigs.has(sig)) {
          continue;
        }
        seenSigs.add(sig);
        deduplicated.push(exp);
      }

      const sorted = deduplicated.sort((a, b) => {
        const timeA = new Date(a.occurred_at || a.created_at || 0).getTime();
        const timeB = new Date(b.occurred_at || b.created_at || 0).getTime();
        return timeB - timeA;
      });
      setSmsExpenses(sorted);
      setSmsTrackingActive(true);
    } catch {
      // SMS expenses are optional — don't break the app
    }
  }, []);

  useEffect(() => {
    void loadSmsExpenses();
  }, [loadSmsExpenses]);

  // ── SMS Expense Tracker hook (Android native only) ───────────────────────
  const token = typeof window !== "undefined" ? localStorage.getItem("jarvis_token") : null;
  useSmsExpenseTracker({
    apiBaseUrl: API_BASE_URL,
    token,
    onExpenseTracked: (expense) => {
      setLastSmsExpense(expense);
      // Refresh SMS expenses list + dashboard after new auto-track
      void loadSmsExpenses();
      void loadDashboard();
      // Clear the "last tracked" toast after 5 seconds
      setTimeout(() => setLastSmsExpense(null), 5000);
    },
  });

  // WebSocket for reminders
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
            new Notification("Jarvis Reminder", { body: message.reminder.task });
          }
        }
      } catch (err) {
        console.error("WebSocket message parsing error:", err);
      }
    };

    return () => ws.close();
  }, []);

  const sendMessage = async (message: string, image?: string) => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || isSending) return;

    setInput("");
    setError("");
    setIsSending(true);
    setMessages((current) => [...current, { role: "user", content: trimmedMessage, image }]);

    try {
      const token = localStorage.getItem("jarvis_token");
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ userId: "default-user", message: trimmedMessage, image }),
      });

      if (response.status === 401) {
        localStorage.clear();
        router.push("/login");
        return;
      }

      if (!response.ok) throw new Error(`Request failed with status ${response.status}`);

      const data = await response.json() as ChatResponse;
      setMessages((current) => [...current, { role: "assistant", content: data.reply, actions: data.actions || [] }]);
      setActions(data.actions || []);
      void loadDashboard();
    } catch {
      setError("Jarvis could not reach the backend.");
    } finally {
      setIsSending(false);
    }
  };

  const acknowledgeReminder = (reminder: Reminder) => {
    const token = localStorage.getItem("jarvis_token");
    fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ userId: "default-user", message: `acknowledge reminder ${reminder._id}` }),
    }).catch(console.error);

    setLiveReminders(prev => prev.filter(r => r._id !== reminder._id));
  };

  // ── Daily Briefing: fetch once per day, cache in localStorage ─────────
  const getTodayKey = () => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  };

  const getBriefingCacheKey = () => {
    const userId = localStorage.getItem("jarvis_user_id");
    return userId ? `jarvis_briefing_cache:${userId}` : null;
  };

  const loadBriefing = useCallback(async (forceRefresh = false) => {
    const token = localStorage.getItem("jarvis_token");
    if (!token) return;
    const cacheKey = getBriefingCacheKey();

    // Check localStorage cache first (unless force-refreshing)
    if (!forceRefresh) {
      try {
        const cached = cacheKey ? localStorage.getItem(cacheKey) : null;
        if (cached) {
          const { date, data } = JSON.parse(cached) as { date: string; data: DailyBriefingData };
          if (date === getTodayKey() && data && data.date_key === date) {
            // Cache hit — use it, no API call needed
            setBriefing(data);
            return;
          }
        }
      } catch {
        // Corrupted cache — continue to fetch
      }
    }

    try {
      setIsBriefingLoading(true);
      const url = `${API_BASE_URL}/api/briefing${forceRefresh ? "?forceRefresh=true" : ""}`;
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json() as DailyBriefingData;
      setBriefing(data);
      // Persist to localStorage with today's date key
      if (cacheKey) {
        localStorage.setItem(cacheKey, JSON.stringify({ date: data.date_key || getTodayKey(), data }));
      }
    } catch {
      // Briefing load failed gracefully
    } finally {
      setIsBriefingLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadBriefing();
  }, [loadBriefing]);

  return (
    <DashboardContext.Provider value={{
      messages, setMessages,
      input, setInput,
      actions,
      dashboard,
      liveReminders,
      dateRange, setDateRange,
      category, setCategory,
      isSending,
      isDashboardLoading,
      error, setError,
      isDarkMode,
      toggleDarkMode,
      userName,
      loadDashboard,
      sendMessage,
      acknowledgeReminder,
      // SMS tracking
      smsExpenses,
      smsTrackingActive,
      lastSmsExpense,
      // Daily Briefing
      briefing,
      isBriefingLoading,
      loadBriefing,
      isBriefingModalOpen,
      setIsBriefingModalOpen,
    }}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (context === undefined) {
    throw new Error("useDashboard must be used within a DashboardProvider");
  }
  return context;
}

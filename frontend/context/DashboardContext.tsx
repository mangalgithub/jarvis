"use client";

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode, FormEvent } from "react";
import { useRouter } from "next/navigation";

// Types
export type Message = {
  role: "user" | "assistant";
  content: string;
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
  loadDashboard: () => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  acknowledgeReminder: (reminder: Reminder) => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:3000";

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

  const sendMessage = async (message: string) => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || isSending) return;

    setInput("");
    setError("");
    setIsSending(true);
    setMessages((current) => [...current, { role: "user", content: trimmedMessage }]);

    try {
      const token = localStorage.getItem("jarvis_token");
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ userId: "default-user", message: trimmedMessage }),
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
      acknowledgeReminder
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

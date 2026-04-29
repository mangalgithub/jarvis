"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
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

type DashboardResponse = {
  finance: {
    summary: FinanceSummary;
    categoryBreakdown: CategoryTotal[];
    budgets: BudgetStatus[];
    recentExpenses: Expense[];
    savingsGoals: SavingsGoal[];
    recurringExpenses: RecurringExpense[];
  } | null;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:3000";

const starterPrompts = [
  "I spent 250 on lunch by UPI",
  "Set food budget 5000 per month",
  "Category wise spending this month",
];

function money(amount = 0) {
  return `Rs ${amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function shortDate(value?: string) {
  if (!value) {
    return "Today";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
  }).format(new Date(value));
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Jarvis is online. Log expenses, set budgets, track income, and watch the dashboard update.",
    },
  ]);
  const [input, setInput] = useState("");
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
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

  const loadDashboard = useCallback(async () => {
    setIsDashboardLoading(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/dashboard?userId=default-user`,
      );

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      setDashboard((await response.json()) as DashboardResponse);
    } catch {
      setError(
        "Jarvis could not load dashboard data. Make sure backend, agents, and MongoDB are running.",
      );
    } finally {
      setIsDashboardLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

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
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          userId: "default-user",
          message: trimmedMessage,
        }),
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const data = (await response.json()) as ChatResponse;

      setMessages((currentMessages) => [
        ...currentMessages,
        { role: "assistant", content: data.reply },
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

  return (
    <main className="min-h-screen bg-[#f6f5f2] text-[#1d1d1f]">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-5 px-4 py-5 lg:grid lg:grid-cols-[260px_1fr] lg:px-6">
        <aside className="flex flex-col justify-between border-r border-[#d8d3ca] bg-[#202124] p-5 text-white lg:min-h-[calc(100vh-40px)]">
          <div>
            <p className="text-sm uppercase tracking-[0.18em] text-[#b9c7c9]">
              Personal OS
            </p>
            <h1 className="mt-3 text-3xl font-semibold">Jarvis</h1>
            <p className="mt-3 text-sm leading-6 text-[#d5d8d5]">
              Finance command center with chat, budgets, income, recurring
              expenses, and savings goals.
            </p>
          </div>

          <div className="mt-8 grid grid-cols-2 gap-3 lg:grid-cols-1">
            <div className="border border-[#454a4d] bg-[#292b2e] p-4">
              <p className="text-xs text-[#b9c7c9]">Backend</p>
              <p className="mt-1 text-sm font-medium">localhost:3000</p>
            </div>
            <div className="border border-[#454a4d] bg-[#292b2e] p-4">
              <p className="text-xs text-[#b9c7c9]">Agents</p>
              <p className="mt-1 text-sm font-medium">localhost:8000</p>
            </div>
          </div>
        </aside>

        <section className="flex flex-col gap-5">
          <div className="grid gap-4 md:grid-cols-5">
            <div className="border border-[#d8d3ca] bg-white p-4">
              <p className="text-sm text-[#6b6b6b]">Today</p>
              <p className="mt-2 text-2xl font-semibold">
                {money(finance?.summary.todayExpenses)}
              </p>
            </div>
            <div className="border border-[#d8d3ca] bg-white p-4">
              <p className="text-sm text-[#6b6b6b]">Month Spend</p>
              <p className="mt-2 text-2xl font-semibold">
                {money(finance?.summary.monthExpenses)}
              </p>
            </div>
            <div className="border border-[#d8d3ca] bg-white p-4">
              <p className="text-sm text-[#6b6b6b]">Month Income</p>
              <p className="mt-2 text-2xl font-semibold">
                {money(finance?.summary.monthIncome)}
              </p>
            </div>
            <div className="border border-[#d8d3ca] bg-white p-4">
              <p className="text-sm text-[#6b6b6b]">Net</p>
              <p className="mt-2 text-2xl font-semibold">
                {money(finance?.summary.monthNet)}
              </p>
            </div>
            <div className="border border-[#d8d3ca] bg-white p-4">
              <p className="text-sm text-[#6b6b6b]">Recurring</p>
              <p className="mt-2 text-2xl font-semibold">
                {money(finance?.summary.recurringMonthly)}
              </p>
            </div>
          </div>

          {error ? (
            <div className="border border-[#d45644] bg-[#fff1ee] px-4 py-3 text-sm text-[#9c2e20]">
              {error}
            </div>
          ) : null}

          <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
            <section className="grid gap-5">
              <div className="grid gap-5 lg:grid-cols-2">
                <section className="border border-[#d8d3ca] bg-white p-5">
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="text-xl font-semibold">Category Spend</h2>
                    <span className="text-xs text-[#6b6b6b]">
                      {isDashboardLoading ? "Loading" : "This month"}
                    </span>
                  </div>
                  <div className="mt-5 space-y-4">
                    {finance?.categoryBreakdown.length ? (
                      finance.categoryBreakdown.map((item) => (
                        <div key={item.category}>
                          <div className="mb-2 flex justify-between gap-3 text-sm">
                            <span className="font-medium">{item.category}</span>
                            <span className="text-[#555]">{money(item.total)}</span>
                          </div>
                          <div className="h-2 bg-[#ece8df]">
                            <div
                              className="h-2 bg-[#245c63]"
                              style={{
                                width: `${Math.max((item.total / maxCategoryTotal) * 100, 4)}%`,
                              }}
                            />
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm leading-6 text-[#6b6b6b]">
                        No category spending yet.
                      </p>
                    )}
                  </div>
                </section>

                <section className="border border-[#d8d3ca] bg-white p-5">
                  <h2 className="text-xl font-semibold">Budgets</h2>
                  <div className="mt-5 space-y-4">
                    {finance?.budgets.length ? (
                      finance.budgets.map((budget) => (
                        <div key={`${budget.category}-${budget.period}`}>
                          <div className="mb-2 flex justify-between gap-3 text-sm">
                            <span className="font-medium">{budget.category}</span>
                            <span className="text-[#555]">
                              {money(budget.spent)} / {money(budget.budget)}
                            </span>
                          </div>
                          <div className="h-2 bg-[#ece8df]">
                            <div
                              className={`h-2 ${
                                budget.progress > 100
                                  ? "bg-[#b94736]"
                                  : "bg-[#5e7f58]"
                              }`}
                              style={{
                                width: `${Math.min(Math.max(budget.progress, 3), 100)}%`,
                              }}
                            />
                          </div>
                          <p className="mt-2 text-xs text-[#6b6b6b]">
                            Remaining {money(budget.remaining)}
                          </p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm leading-6 text-[#6b6b6b]">
                        No budgets set yet.
                      </p>
                    )}
                  </div>
                </section>
              </div>

              <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
                <section className="flex min-h-[500px] flex-col border border-[#d8d3ca] bg-white">
                  <div className="border-b border-[#d8d3ca] px-5 py-4">
                    <h2 className="text-xl font-semibold">Chat</h2>
                  </div>

                  <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
                    {messages.map((message, index) => (
                      <div
                        className={`flex ${
                          message.role === "user"
                            ? "justify-end"
                            : "justify-start"
                        }`}
                        key={`${message.role}-${index}`}
                      >
                        <div
                          className={`max-w-[78%] px-4 py-3 text-sm leading-6 ${
                            message.role === "user"
                              ? "bg-[#245c63] text-white"
                              : "bg-[#f0eee9] text-[#1d1d1f]"
                          }`}
                        >
                          {message.content}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="border-t border-[#d8d3ca] p-4">
                    <div className="mb-3 flex flex-wrap gap-2">
                      {starterPrompts.map((prompt) => (
                        <button
                          className="border border-[#c9c4ba] px-3 py-2 text-xs font-medium text-[#3b3b3d] hover:bg-[#f0eee9]"
                          key={prompt}
                          onClick={() => void sendMessage(prompt)}
                          type="button"
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>

                    <form className="flex gap-3" onSubmit={handleSubmit}>
                      <input
                        className="min-h-12 flex-1 border border-[#c9c4ba] px-4 text-sm outline-none focus:border-[#245c63]"
                        onChange={(event) => setInput(event.target.value)}
                        placeholder="Tell Jarvis what to do..."
                        value={input}
                      />
                      <button
                        className="min-h-12 bg-[#202124] px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#8e8e8e]"
                        disabled={isSending}
                        type="submit"
                      >
                        {isSending ? "Sending" : "Send"}
                      </button>
                    </form>
                  </div>
                </section>

                <aside className="border border-[#d8d3ca] bg-white p-5">
                  <h2 className="text-xl font-semibold">Recent Expenses</h2>
                  <div className="mt-4 space-y-3">
                    {finance?.recentExpenses.length ? (
                      finance.recentExpenses.map((expense) => (
                        <div
                          className="border-b border-[#ece8df] pb-3 last:border-b-0"
                          key={expense._id}
                        >
                          <div className="flex justify-between gap-3 text-sm">
                            <span className="font-medium">
                              {expense.description}
                            </span>
                            <span>{money(expense.amount)}</span>
                          </div>
                          <p className="mt-1 text-xs text-[#6b6b6b]">
                            {expense.category} |{" "}
                            {expense.payment_method || "unknown"} |{" "}
                            {shortDate(expense.occurred_at || expense.created_at)}
                          </p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm leading-6 text-[#6b6b6b]">
                        No expenses logged yet.
                      </p>
                    )}
                  </div>
                </aside>
              </div>
            </section>

            <aside className="grid gap-5">
              <section className="border border-[#d8d3ca] bg-white p-5">
                <h2 className="text-xl font-semibold">Savings Goals</h2>
                <div className="mt-4 space-y-4">
                  {finance?.savingsGoals.length ? (
                    finance.savingsGoals.map((goal) => {
                      const saved = goal.saved_amount || 0;
                      const progress = goal.target_amount
                        ? Math.min((saved / goal.target_amount) * 100, 100)
                        : 0;

                      return (
                        <div key={goal._id}>
                          <div className="mb-2 flex justify-between gap-3 text-sm">
                            <span className="font-medium">{goal.name}</span>
                            <span className="text-[#555]">
                              {money(saved)} / {money(goal.target_amount)}
                            </span>
                          </div>
                          <div className="h-2 bg-[#ece8df]">
                            <div
                              className="h-2 bg-[#806b3a]"
                              style={{ width: `${Math.max(progress, 3)}%` }}
                            />
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-sm leading-6 text-[#6b6b6b]">
                      No savings goals yet.
                    </p>
                  )}
                </div>
              </section>

              <section className="border border-[#d8d3ca] bg-white p-5">
                <h2 className="text-xl font-semibold">Recurring</h2>
                <div className="mt-4 space-y-3">
                  {finance?.recurringExpenses.length ? (
                    finance.recurringExpenses.map((item) => (
                      <div
                        className="flex justify-between gap-3 border-b border-[#ece8df] pb-3 text-sm last:border-b-0"
                        key={item._id}
                      >
                        <div>
                          <p className="font-medium">{item.description}</p>
                          <p className="mt-1 text-xs text-[#6b6b6b]">
                            {item.category} | {item.frequency || "monthly"}
                          </p>
                        </div>
                        <span>{money(item.amount)}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm leading-6 text-[#6b6b6b]">
                      No recurring expenses yet.
                    </p>
                  )}
                </div>
              </section>

              <section className="border border-[#d8d3ca] bg-white p-5">
                <h2 className="text-xl font-semibold">Agent Actions</h2>
                <div className="mt-4 space-y-3">
                  {actions.length ? (
                    actions.map((action, index) => (
                      <div
                        className="border border-[#e2ddd4] bg-[#faf9f6] p-3"
                        key={`${action.type}-${index}`}
                      >
                        <p className="text-sm font-semibold">{action.type}</p>
                        <pre className="mt-2 overflow-x-auto text-xs leading-5 text-[#555]">
                          {JSON.stringify(action, null, 2)}
                        </pre>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm leading-6 text-[#6b6b6b]">
                      Agent results will appear here after Jarvis handles a
                      command.
                    </p>
                  )}
                </div>
              </section>
            </aside>
          </div>
        </section>
      </div>
    </main>
  );
}

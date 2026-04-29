"use client";

import { FormEvent, useMemo, useState } from "react";

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

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:3000";

const starterPrompts = [
  "I spent 250 on lunch and 100 on tea",
  "Track 1200 rupees for grocery",
  "How much did I spend today?",
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Jarvis is online. Start by logging an expense, like: I spent 250 on lunch.",
    },
  ]);
  const [input, setInput] = useState("");
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");

  const financeActions = useMemo(
    () => actions.filter((action) => action.type.startsWith("expense")),
    [actions],
  );

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
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-5 px-4 py-5 lg:grid lg:grid-cols-[280px_1fr] lg:px-6">
        <aside className="flex flex-col justify-between border-r border-[#d8d3ca] bg-[#202124] p-5 text-white lg:min-h-[calc(100vh-40px)]">
          <div>
            <p className="text-sm uppercase tracking-[0.18em] text-[#b9c7c9]">
              Personal OS
            </p>
            <h1 className="mt-3 text-3xl font-semibold">Jarvis</h1>
            <p className="mt-3 text-sm leading-6 text-[#d5d8d5]">
              One command center for expenses, health, news, learning, and
              market research.
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
          <div className="grid gap-4 md:grid-cols-3">
            <div className="border border-[#d8d3ca] bg-white p-4">
              <p className="text-sm text-[#6b6b6b]">Finance Agent</p>
              <p className="mt-2 text-2xl font-semibold">Active</p>
            </div>
            <div className="border border-[#d8d3ca] bg-white p-4">
              <p className="text-sm text-[#6b6b6b]">Last Actions</p>
              <p className="mt-2 text-2xl font-semibold">{actions.length}</p>
            </div>
            <div className="border border-[#d8d3ca] bg-white p-4">
              <p className="text-sm text-[#6b6b6b]">MongoDB</p>
              <p className="mt-2 text-2xl font-semibold">
                {financeActions.length ? "Writing" : "Ready"}
              </p>
            </div>
          </div>

          <div className="grid min-h-[620px] gap-5 xl:grid-cols-[1fr_340px]">
            <section className="flex min-h-[560px] flex-col border border-[#d8d3ca] bg-white">
              <div className="border-b border-[#d8d3ca] px-5 py-4">
                <h2 className="text-xl font-semibold">Chat</h2>
              </div>

              <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
                {messages.map((message, index) => (
                  <div
                    className={`flex ${
                      message.role === "user" ? "justify-end" : "justify-start"
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

              {error ? (
                <div className="mx-5 mb-3 border border-[#d45644] bg-[#fff1ee] px-4 py-3 text-sm text-[#9c2e20]">
                  {error}
                </div>
              ) : null}

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
            </aside>
          </div>
        </section>
      </div>
    </main>
  );
}

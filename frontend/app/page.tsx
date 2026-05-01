"use client";

import { useDashboard } from "@/context/DashboardContext";
import { PanelCard } from "@/components/dashboard/PanelCard";
import { money, shortDate } from "@/lib/utils";
import { useSpeechToText } from "@/hooks/useSpeechToText";
import { useEffect, useRef } from "react";

const starterPrompts = [
  "I spent 250 on lunch by UPI",
  "Set food budget 5000 per month",
  "Drank 2 glasses of water",
  "Remember I am vegetarian",
  "Nifty 50 today",
  "Reliance stock price",
  "Roadmap to learn Python",
  "Remind me to check emails at 5pm",
];

export default function Home() {
  const { 
    messages, 
    input, 
    setInput, 
    isSending, 
    error, 
    sendMessage,
    liveReminders,
    acknowledgeReminder,
    userName
  } = useDashboard();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { isListening, transcript, startListening, stopListening } = useSpeechToText();

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript, setInput]);

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void sendMessage(input);
  };

  return (
    <div className="flex flex-col h-screen max-w-[1200px] mx-auto p-4 sm:p-6 lg:p-8">
      {/* Header */}
      <header className="mb-8 flex items-end justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-600 dark:text-cyan-400">Command Center</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 dark:text-white">Hello, {userName}</h1>
        </div>
        {liveReminders.length > 0 && (
          <div className="flex gap-2">
            {liveReminders.map(r => (
              <div key={r._id} className="animate-bounce flex items-center gap-2 rounded-full bg-amber-100 px-4 py-2 text-xs font-bold text-amber-700 dark:bg-amber-500/20 dark:text-amber-400 border border-amber-200 dark:border-amber-500/30">
                🔔 {r.task}
                <button onClick={() => acknowledgeReminder(r)} className="hover:text-amber-900 dark:hover:text-amber-200">×</button>
              </div>
            ))}
          </div>
        )}
      </header>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-h-0 bg-white/50 backdrop-blur-md rounded-[32px] border border-slate-200/50 shadow-2xl dark:bg-slate-900/50 dark:border-white/5 overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-[24px] px-6 py-4 text-sm font-medium leading-relaxed shadow-sm ${
                msg.role === "user"
                  ? "bg-slate-950 text-white dark:bg-white dark:text-slate-950"
                  : "bg-slate-100 text-slate-800 dark:bg-white/10 dark:text-slate-200"
              }`}>
                {msg.content}
                {msg.actions && msg.actions.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-current/10 flex flex-wrap gap-2">
                    {msg.actions.map((act, j) => (
                      <span key={j} className="text-[10px] font-bold uppercase tracking-wider opacity-70">
                        ⚡ {act.type.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {isSending && (
            <div className="flex justify-start">
              <div className="bg-slate-100 rounded-full px-6 py-3 dark:bg-white/10">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" />
                  <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                  <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            </div>
          )}
          {error && (
            <div className="flex justify-center">
              <p className="bg-rose-50 text-rose-600 px-4 py-2 rounded-full text-xs font-bold dark:bg-rose-500/10 dark:text-rose-400">
                ⚠️ {error}
              </p>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Actions */}
        <div className="px-6 py-4 bg-slate-50/50 dark:bg-white/5 border-t border-slate-100 dark:border-white/5 overflow-x-auto no-scrollbar">
          <div className="flex gap-2 whitespace-nowrap">
            {starterPrompts.map(p => (
              <button
                key={p}
                onClick={() => sendMessage(p)}
                className="px-4 py-2 rounded-full border border-slate-200 bg-white text-xs font-bold text-slate-600 hover:bg-slate-50 transition dark:border-white/10 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/20"
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar */}
        <div className="p-6">
          <form onSubmit={handleFormSubmit} className="relative flex items-center gap-3">
            <div className="relative flex-1 flex items-center">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={isListening ? "Listening..." : "Tell Jarvis what to do..."}
                className={`w-full bg-slate-100 rounded-full py-4 pl-6 pr-16 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:bg-white/10 dark:text-white transition-all ${
                  isListening ? "ring-2 ring-cyan-500 bg-cyan-500/5" : ""
                }`}
              />
              <button
                type="submit"
                disabled={isSending || !input.trim()}
                className="absolute right-2 h-10 w-10 flex items-center justify-center rounded-full bg-slate-950 text-white disabled:opacity-50 transition-all active:scale-95 dark:bg-white dark:text-slate-950"
              >
                <span className="text-xl">↑</span>
              </button>
            </div>
            <button
              type="button"
              onClick={isListening ? stopListening : startListening}
              className={`h-12 w-12 flex items-center justify-center rounded-full transition-all duration-300 ${
                isListening 
                  ? "bg-rose-500 text-white animate-pulse scale-110 shadow-lg shadow-rose-500/20" 
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-white/10 dark:text-white"
              }`}
            >
              <span className="text-xl">{isListening ? "⏹" : "🎤"}</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
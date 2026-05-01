"use client";

import { useState } from "react";
import { useDashboard } from "@/context/DashboardContext";
import { PanelCard } from "@/components/dashboard/PanelCard";

const NEWS_TABS = [
  { key: "india", label: "🇮🇳 India" },
  { key: "world", label: "🌍 World" },
  { key: "ai", label: "🤖 AI" },
];

export default function NewsPage() {
  const { dashboard, sendMessage } = useDashboard();
  const [activeTab, setActiveTab] = useState<string>("india");
  const news = dashboard?.news;

  if (!news) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <p className="text-slate-500 animate-pulse">Loading news briefings...</p>
      </div>
    );
  }

  const categoryData = news[activeTab];
  const articles = categoryData?.articles ?? [];

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1400px] mx-auto">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 dark:text-white">Daily Briefings</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Stay updated with the latest news curated for you.
          </p>
        </div>
        <button
          onClick={() => sendMessage("Morning briefing")}
          className="rounded-xl bg-slate-950 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-slate-950/20 transition-all hover:-translate-y-0.5 active:translate-y-0 dark:bg-white dark:text-slate-950"
        >
          📰 Refresh Briefing
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-white/10">
        {NEWS_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-6 py-3 text-sm font-bold transition-all ${
              activeTab === tab.key
                ? "border-b-2 border-cyan-500 text-cyan-600 dark:text-cyan-400"
                : "text-slate-500 hover:text-slate-800 dark:hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {articles.length === 0 ? (
          <p className="text-slate-500">No articles found in this category.</p>
        ) : (
          articles.map((article, idx) => (
            <PanelCard key={idx} className="flex flex-col h-full">
              {article.image_url && (
                <img 
                  src={article.image_url} 
                  alt={article.title}
                  className="mb-4 h-40 w-full rounded-2xl object-cover"
                />
              )}
              <div className="flex-1">
                <span className="text-[10px] font-bold uppercase tracking-widest text-cyan-600 dark:text-cyan-400">
                  {article.source || "News"}
                </span>
                <h3 className="mt-1 line-clamp-2 text-sm font-bold leading-tight text-slate-950 dark:text-white">
                  {article.title}
                </h3>
                <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                  {article.description}
                </p>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <a 
                  href={article.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-xs font-bold text-blue-600 hover:underline"
                >
                  Read More →
                </a>
                <button
                  onClick={() => sendMessage(`summarize news: ${article.title}`)}
                  className="rounded-lg bg-slate-100 p-2 text-xs hover:bg-slate-200 dark:bg-white/5"
                >
                  🤖 Ask
                </button>
              </div>
            </PanelCard>
          ))
        )}
      </div>
    </div>
  );
}

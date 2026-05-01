"use client";

import { useDashboard } from "@/context/DashboardContext";
import { PanelCard, SectionTitle } from "@/components/dashboard/PanelCard";

export default function MarketsPage() {
  const { dashboard, sendMessage } = useDashboard();
  const stocks = dashboard?.stocks;

  if (!stocks) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <p className="text-slate-500 animate-pulse">Loading market data...</p>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1400px] mx-auto">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 dark:text-white">Market Insights</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Real-time tracking of indices and your portfolio.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => sendMessage("Top gainers today")}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-bold hover:bg-slate-50 dark:border-white/10 dark:hover:bg-white/5"
          >
            📈 Top Gainers
          </button>
          <button
            onClick={() => sendMessage("Nifty 50 today")}
            className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-bold text-white dark:bg-white dark:text-slate-950"
          >
            📊 Refresh
          </button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {stocks.indices.map((idx) => {
          const isPositive = idx.change_pct >= 0;
          return (
            <PanelCard key={idx.symbol} className="relative">
               <div className="flex items-center justify-between">
                 <div>
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">{idx.name}</h3>
                    <p className="text-sm font-medium text-slate-500">{idx.symbol}</p>
                 </div>
                 <div className={`text-right ${isPositive ? "text-emerald-500" : "text-rose-500"}`}>
                    <p className="text-2xl font-black">{idx.price.toLocaleString("en-IN")}</p>
                    <p className="text-sm font-bold">
                      {isPositive ? "▲" : "▼"} {Math.abs(idx.change).toFixed(2)} ({Math.abs(idx.change_pct).toFixed(2)}%)
                    </p>
                 </div>
               </div>

               <div className="mt-6 flex gap-2">
                 <button
                    onClick={() => sendMessage(`${idx.name} performance this month`)}
                    className="flex-1 rounded-xl bg-slate-100 py-2 text-xs font-bold transition hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10"
                 >
                   Chart
                 </button>
                 <button
                    onClick={() => sendMessage(`latest news on ${idx.name}`)}
                    className="flex-1 rounded-xl bg-slate-100 py-2 text-xs font-bold transition hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10"
                 >
                   News
                 </button>
               </div>
            </PanelCard>
          );
        })}
      </div>

      <PanelCard className="mt-8">
        <SectionTitle title="Mutual Funds & Stocks" />
        <p className="text-sm text-slate-500 mb-6">Track your investments by asking Jarvis. Try commands like "Axis bluechip mutual fund NAV".</p>
        <div className="flex flex-wrap gap-2">
           {["Axis Bluechip Fund", "SBI Small Cap", "Reliance Stock", "TCS Price"].map(s => (
             <button
               key={s}
               onClick={() => sendMessage(s)}
               className="rounded-full bg-slate-100 px-4 py-2 text-xs font-bold hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10"
             >
               {s}
             </button>
           ))}
        </div>
      </PanelCard>
    </div>
  );
}

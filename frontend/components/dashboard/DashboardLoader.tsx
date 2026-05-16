"use client";

/**
 * Full-page skeleton loader displayed while the dashboard is loading.
 * Uses shimmer animations to signal that content is on the way.
 */
export function DashboardLoader({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1400px] mx-auto animate-in fade-in duration-300">
      {/* Header skeleton */}
      <div className="space-y-2">
        <div className="h-8 w-56 rounded-xl bg-slate-200 dark:bg-white/10 shimmer" />
        <div className="h-4 w-80 rounded-lg bg-slate-100 dark:bg-white/5 shimmer" />
      </div>

      {/* Metric cards skeleton */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-white/10 dark:bg-white/5 space-y-3"
          >
            <div className="h-3 w-20 rounded bg-slate-200 dark:bg-white/10 shimmer" />
            <div className="h-7 w-28 rounded-lg bg-slate-200 dark:bg-white/10 shimmer" />
          </div>
        ))}
      </div>

      {/* Chart skeleton */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-white/10 dark:bg-white/5">
        <div className="h-4 w-40 rounded bg-slate-200 dark:bg-white/10 shimmer mb-4" />
        <div className="h-48 rounded-xl bg-slate-100 dark:bg-white/5 shimmer" />
      </div>

      {/* Cards grid skeleton */}
      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-white/10 dark:bg-white/5 space-y-4"
          >
            <div className="h-4 w-32 rounded bg-slate-200 dark:bg-white/10 shimmer" />
            {Array.from({ length: 3 }).map((_, j) => (
              <div key={j} className="space-y-2">
                <div className="flex justify-between">
                  <div className="h-3 w-24 rounded bg-slate-200 dark:bg-white/10 shimmer" />
                  <div className="h-3 w-16 rounded bg-slate-200 dark:bg-white/10 shimmer" />
                </div>
                <div className="h-2 rounded-full bg-slate-200 dark:bg-white/10 shimmer" />
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Floating label */}
      <div className="fixed bottom-24 left-1/2 -translate-x-1/2 lg:left-[calc(50%+128px)] z-50">
        <div className="flex items-center gap-3 rounded-full bg-slate-950 px-6 py-3 shadow-2xl dark:bg-white">
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce dark:bg-cyan-600" />
            <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce [animation-delay:0.2s] dark:bg-cyan-600" />
            <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce [animation-delay:0.4s] dark:bg-cyan-600" />
          </div>
          <span className="text-xs font-bold text-white dark:text-slate-950">{label}</span>
        </div>
      </div>
    </div>
  );
}

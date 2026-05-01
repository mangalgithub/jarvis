"use client";

import { Card } from "@heroui/react";
import { money } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: number | undefined;
}

export function MetricCard({ label, value }: MetricCardProps) {
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

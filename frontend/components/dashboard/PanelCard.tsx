"use client";

import { Card } from "@heroui/react";
import { ReactNode } from "react";

interface PanelCardProps {
  children: ReactNode;
  className?: string;
}

export function PanelCard({ children, className = "" }: PanelCardProps) {
  return (
    <Card className={`rounded-3xl border border-slate-200/80 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur dark:border-white/10 dark:bg-white/5 dark:shadow-[0_10px_30px_rgba(0,0,0,0.35)] ${className}`}>
      {children}
    </Card>
  );
}

export function SectionTitle({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) {
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

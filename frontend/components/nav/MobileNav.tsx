"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { name: "Chat", path: "/", icon: "💬" },
  { name: "Finance", path: "/finance", icon: "💰" },
  { name: "Health", path: "/health", icon: "🏥" },
  { name: "News", path: "/news", icon: "📰" },
  { name: "Profile", path: "/profile", icon: "👤" },
];

export default function MobileNav() {
  const pathname = usePathname();

  return (
    <div className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-xl border-t border-slate-200/50 dark:bg-slate-950/80 dark:border-white/10 px-4 py-2">
      <div className="flex justify-between items-center max-w-md mx-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link
              key={item.path}
              href={item.path}
              className={`flex flex-col items-center p-2 rounded-2xl transition-all ${
                isActive 
                  ? "text-cyan-600 dark:text-cyan-400 scale-110" 
                  : "text-slate-500 dark:text-slate-500"
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="text-[10px] font-bold uppercase mt-1">{item.name}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

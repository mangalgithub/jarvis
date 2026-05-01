"use client";

import "./globals.css";
import { DashboardProvider } from "@/context/DashboardContext";
import Sidebar from "@/components/nav/Sidebar";
import MobileNav from "@/components/nav/MobileNav";
import { usePathname } from "next/navigation";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname === "/login" || pathname === "/register";

  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-950 dark:bg-slate-950 dark:text-white transition-colors duration-300">
        <DashboardProvider>
          {!isAuthPage && <Sidebar />}
          <main className={!isAuthPage ? "lg:pl-64 pb-20 lg:pb-0" : ""}>
            {children}
          </main>
          {!isAuthPage && <MobileNav />}
        </DashboardProvider>
      </body>
    </html>
  );
}
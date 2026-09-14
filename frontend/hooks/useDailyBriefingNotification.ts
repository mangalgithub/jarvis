"use client";

import { useEffect, useRef } from "react";

interface UseDailyBriefingNotificationOptions {
  onOpenBriefing: () => void;
  userName?: string;
}

export function useDailyBriefingNotification({
  onOpenBriefing,
  userName = "User",
}: UseDailyBriefingNotificationOptions) {
  const initialized = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined" || initialized.current) return;
    initialized.current = true;

    const checkAndTriggerMorningNotification = () => {
      if (localStorage.getItem("jarvis_briefing_notifications_enabled") !== "true") return;
      const now = new Date();
      const todayDateStr = now.toISOString().split("T")[0];
      const lastShownDate = localStorage.getItem("jarvis_last_briefing_notification_date");

      // Check if already notified today
      if (lastShownDate === todayDateStr) return;

      // Check if current hour is between 7:00 AM and 12:00 PM (morning window)
      const currentHour = now.getHours();
      if (currentHour >= 7 && currentHour <= 12) {
        if ("Notification" in window && Notification.permission === "granted") {
          try {
            const notif = new Notification("🌅 Today with Jarvis", {
              body: `Good morning ${userName}! Your daily briefing is ready. Check your spending pace, health goals, and today's priorities.`,
              icon: "/favicon.ico",
            });

            notif.onclick = () => {
              window.focus();
              onOpenBriefing();
            };

            localStorage.setItem("jarvis_last_briefing_notification_date", todayDateStr);
          } catch {
            // Notification failed gracefully
          }
        }
      }
    };

    // Check on mount
    checkAndTriggerMorningNotification();

    // Check every 30 minutes in case app is kept open
    const interval = setInterval(checkAndTriggerMorningNotification, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, [onOpenBriefing, userName]);
}

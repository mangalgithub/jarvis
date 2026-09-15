"use client";

import { Capacitor } from "@capacitor/core";

const DAILY_BRIEFING_NOTIFICATION_ID = 10_001;

export const isNativeNotificationPlatform = () => {
  try {
    return typeof window !== "undefined" && Capacitor.isNativePlatform();
  } catch {
    return false;
  }
};

export async function enableDailyBriefingNotifications(): Promise<string> {
  if (isNativeNotificationPlatform()) {
    try {
      const { LocalNotifications } = await import("@capacitor/local-notifications");
      const currentPermission = await LocalNotifications.checkPermissions();
      let permission = currentPermission;

      if (currentPermission.display !== "granted") {
        permission = await LocalNotifications.requestPermissions();
      }

      if (permission.display !== "granted") {
        throw new Error("Android notification permission was not granted. Please allow notifications in App Settings.");
      }

      try {
        await LocalNotifications.createChannel({
          id: "daily_briefing",
          name: "Daily Briefing",
          description: "Your morning Today with Jarvis reminder",
          importance: 4,
          vibration: true,
        });
      } catch (channelErr) {
        console.warn("[LocalNotifications] createChannel warning:", channelErr);
      }

      await LocalNotifications.cancel({ notifications: [{ id: DAILY_BRIEFING_NOTIFICATION_ID }] });
      await LocalNotifications.schedule({
        notifications: [{
          id: DAILY_BRIEFING_NOTIFICATION_ID,
          title: "🌅 Today with Jarvis",
          body: "Your daily briefing is ready. Check your spending pace, health goals, and priorities.",
          channelId: "daily_briefing",
          schedule: { on: { hour: 8, minute: 0 }, repeats: true, allowWhileIdle: true },
          isExactNotification: false,
          extra: { destination: "daily-briefing" },
        }],
      });
      return "Daily 8:00 AM Android reminder enabled!";
    } catch (err: any) {
      console.error("[LocalNotifications] Failed to enable:", err);
      throw new Error(err?.message || "Failed to schedule Android notification.");
    }
  }

  if (typeof window === "undefined" || !("Notification" in window)) {
    throw new Error("Notifications are not supported in this browser environment.");
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Browser notification permission was not granted.");
  }
  return "Morning browser reminders enabled while Jarvis is open.";
}

export async function disableDailyBriefingNotifications(): Promise<string> {
  if (isNativeNotificationPlatform()) {
    try {
      const { LocalNotifications } = await import("@capacitor/local-notifications");
      await LocalNotifications.cancel({ notifications: [{ id: DAILY_BRIEFING_NOTIFICATION_ID }] });
      return "Android daily briefing reminders disabled.";
    } catch (err: any) {
      console.error("[LocalNotifications] Failed to disable:", err);
      return "Android daily briefing reminders disabled.";
    }
  }
  return "Morning browser reminders disabled.";
}


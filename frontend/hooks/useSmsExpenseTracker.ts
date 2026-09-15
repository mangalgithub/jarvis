"use client";

/**
 * useSmsExpenseTracker — React hook for automatic SMS expense tracking.
 *
 * On Android native:
 *   1. Requests READ_SMS + RECEIVE_SMS permissions on first mount
 *   2. Reads last 50 SMS messages from inbox and sends any unprocessed
 *      payment messages to the Jarvis backend (initial sync)
 *   3. Listens for new SMS in real-time and immediately sends new
 *      payment messages to the backend
 *   4. Saves JWT token to Android SharedPreferences so SmsListenerService
 *      can make authenticated backend calls even when the app is closed
 *
 * On web/desktop:
 *   - Does nothing (SMS reading is not available)
 *
 * Designed specifically for Realme 9 5G (Realme UI / Android 12).
 */

import { useEffect, useRef, useCallback } from "react";
import SmsPlugin, { isAndroidNative, SmsMessage } from "@/src/plugins/SmsPlugin";
import { Capacitor } from "@capacitor/core";

const PAYMENT_SENDER_CODES = [
  "GPAY", "PHONEPE", "PPAY", "PAYTM", "BOIINB", "HDFCBK", "SBIINB",
  "ICICIB", "AXISBK", "KOTAKB", "AMAZON", "UPIBNK", "CANBNK", "UNIONB",
  "FEDBNK", "IDFCBK", "PNBSMS", "YESBNK", "INDUSB", "BANK", "CARDS",
];

// Keyword fallback for unknown sender IDs
const PAYMENT_KEYWORDS = [
  "debited", "debit", "paid", "payment", "upi", "imps", "neft",
  "credited", "purchase", "spent", "txn", "ref", "a/c",
];

function isPaymentSms(sender: string, body: string): boolean {
  const senderUp = (sender || "").toUpperCase().trim();
  if (PAYMENT_SENDER_CODES.some(code => senderUp.includes(code))) return true;
  const bodyLower = (body || "").toLowerCase();
  return PAYMENT_KEYWORDS.some(kw => bodyLower.includes(kw));
}

// ─── Hook options ─────────────────────────────────────────────────────────────
interface UseSmsExpenseTrackerOptions {
  apiBaseUrl: string;
  token: string | null;
  onExpenseTracked?: (expense: {
    amount: number;
    description: string;
    category: string;
    bank: string;
  }) => void;
  onError?: (err: string) => void;
}

export function useSmsExpenseTracker({
  apiBaseUrl,
  token,
  onExpenseTracked,
  onError,
}: UseSmsExpenseTrackerOptions) {
  const initialized = useRef(false);
  const listenerRef = useRef<{ remove: () => void } | null>(null);

  // ─── Save token to SharedPreferences for SmsListenerService ────────────────
  const persistTokenToNative = useCallback((jwt: string) => {
    if (!isAndroidNative()) return;
    // Use Capacitor's Preferences plugin to persist token
    // so SmsListenerService (Java) can read it via SharedPreferences
    try {
      // @ts-ignore — accessing Android bridge directly
      (Capacitor as any).toNative("Preferences", "set", { key: "jwt_token", value: jwt });
    } catch {
      // Preferences plugin may not be installed — that's fine
    }
  }, []);

  // ─── POST a single SMS to the backend ────────────────────────────────────
  const sendSmsToBackend = useCallback(async (msg: SmsMessage) => {
    if (!token) return;

    try {
      const response = await fetch(`${apiBaseUrl}/api/expenses/sms`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          sms_body: msg.body,
          sender: msg.sender,
          received_at: msg.timestamp,
        }),
      });

      if (!response.ok) return;

      const data = await response.json();
      if (data.success && data.expense && onExpenseTracked) {
        onExpenseTracked({
          amount: data.expense.amount,
          description: data.expense.description,
          category: data.expense.category,
          bank: data.expense.bank || "",
        });
      }
    } catch (e) {
      // Silently ignore network errors — service will retry from Java side
    }
  }, [apiBaseUrl, token, onExpenseTracked]);

  // ─── Initial inbox sync (runs once after permissions granted) ────────────
  const syncInbox = useCallback(async () => {
    try {
      const { messages } = await SmsPlugin.readInbox({ count: 50 });
      const paymentSms = messages.filter(m => isPaymentSms(m.sender, m.body));

      if (paymentSms.length === 0) return;

      // Deduplicate inbox messages locally before sending to prevent duplicate dispatch
      const seen = new Set<string>();
      const distinctMessages: SmsMessage[] = [];
      for (const msg of paymentSms) {
        const key = (msg.body || "").trim();
        if (key && !seen.has(key)) {
          seen.add(key);
          distinctMessages.push(msg);
        }
      }

      // Send in sequence to avoid hammering the backend
      for (const msg of distinctMessages) {
        await sendSmsToBackend(msg);
        // Small delay between requests
        await new Promise(r => setTimeout(r, 200));
      }
    } catch (e) {
      console.error("[SmsTracker] Inbox sync failed:", e);
    }
  }, [sendSmsToBackend]);

  // ─── Initialize permissions + listener ───────────────────────────────────
  useEffect(() => {
    if (!isAndroidNative() || !token || initialized.current) return;

    const init = async () => {
      initialized.current = true;

      // Persist token for SmsListenerService (background Java code)
      persistTokenToNative(token);

      // 1. Check current permissions
      const current = await SmsPlugin.checkPermissions();
      let hasPermissions = current.read === "granted" && current.receive === "granted";

      // 2. Request if not granted
      if (!hasPermissions) {
        const requested = await SmsPlugin.requestPermissions();
        hasPermissions = requested.read === "granted" && requested.receive === "granted";
      }

      if (!hasPermissions) {
        onError?.("SMS permission denied. Auto expense tracking won't work.");
        return;
      }

      // 3. Sync existing inbox (catch up on recent payments)
      await syncInbox();

      // 4. Listen for new SMS in real-time
      listenerRef.current = await SmsPlugin.addListener("onSmsReceived", (msg) => {
        if (isPaymentSms(msg.sender, msg.body)) {
          void sendSmsToBackend(msg);
        }
      });
    };

    void init();

    return () => {
      listenerRef.current?.remove();
      listenerRef.current = null;
      initialized.current = false;
    };
  }, [token, persistTokenToNative, syncInbox, sendSmsToBackend, onError]);
}

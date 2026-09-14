/**
 * SmsPlugin.ts — TypeScript bridge for the native Android SmsPlugin.
 *
 * This module wraps the Capacitor plugin so it can be used from
 * any React component or hook with full type safety.
 *
 * On web/desktop (when running in browser), all calls are gracefully
 * no-op'd so the app works during development without errors.
 */

import { registerPlugin, Capacitor } from '@capacitor/core';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SmsPermissions {
  read: 'granted' | 'denied' | 'prompt';
  receive: 'granted' | 'denied' | 'prompt';
}

export interface SmsMessage {
  sender: string;
  body: string;
  timestamp: string; // ISO 8601
}

export interface ReadInboxResult {
  messages: SmsMessage[];
}

export interface SmsPluginDefinition {
  checkPermissions(): Promise<SmsPermissions>;
  requestPermissions(): Promise<SmsPermissions>;
  readInbox(options: { count: number }): Promise<ReadInboxResult>;
  addListener(
    event: 'onSmsReceived',
    callback: (message: SmsMessage) => void
  ): Promise<{ remove: () => void }>;
}

// ─── Register plugin ──────────────────────────────────────────────────────────

const SmsPlugin = registerPlugin<SmsPluginDefinition>('SmsPlugin', {
  // Web fallback — no-op implementations so dev server doesn't crash
  web: {
    checkPermissions: async () => ({ read: 'denied', receive: 'denied' }),
    requestPermissions: async () => ({ read: 'denied', receive: 'denied' }),
    readInbox: async () => ({ messages: [] }),
    addListener: async () => ({ remove: () => {} }),
  },
});

export default SmsPlugin;

// ─── Helper: is running as native Android app ─────────────────────────────────

export const isAndroidNative = () => Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android';

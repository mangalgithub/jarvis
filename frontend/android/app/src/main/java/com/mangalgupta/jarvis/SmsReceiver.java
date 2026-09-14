package com.mangalgupta.jarvis;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.provider.Telephony;
import android.telephony.SmsMessage;
import android.util.Log;

import androidx.core.content.ContextCompat;

/**
 * SmsReceiver - BroadcastReceiver for incoming SMS messages.
 *
 * Registered in AndroidManifest.xml with the SMS_RECEIVED action.
 * Works on Realme 9 5G (Android 12 / Realme UI 3.0) because
 * BroadcastReceivers for SMS_RECEIVED are woken up by the system
 * even when the app is in the background, as long as the app has
 * the RECEIVE_SMS permission granted.
 *
 * ── Routing Logic ───────────────────────────────────────────────────────────
 * 1. ALWAYS fire the Capacitor JS bridge event (SmsPlugin.onSmsReceived).
 *    The JS hook (useSmsExpenseTracker.ts) will deduplicate and POST to backend.
 *
 * 2. ONLY start SmsListenerService (native fallback) when the JS bridge is
 *    inactive (app fully backgrounded, WebView destroyed).
 *    This prevents the double-POST that caused duplicate expense entries.
 * ────────────────────────────────────────────────────────────────────────────
 *
 * Flow:
 *   SMS arrives → onReceive() → SmsPlugin.onSmsReceived() (JS bridge)
 *                             → SmsListenerService ONLY if JS bridge is inactive
 */
public class SmsReceiver extends BroadcastReceiver {

    private static final String TAG = "JarvisSmsReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!Telephony.Sms.Intents.SMS_RECEIVED_ACTION.equals(intent.getAction())) {
            return;
        }

        // Check permission at runtime
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECEIVE_SMS)
                != PackageManager.PERMISSION_GRANTED) {
            Log.w(TAG, "RECEIVE_SMS permission not granted — skipping");
            return;
        }

        SmsMessage[] messages = Telephony.Sms.Intents.getMessagesFromIntent(intent);
        if (messages == null || messages.length == 0) return;

        // Reassemble multi-part SMS into a single body
        StringBuilder bodyBuilder = new StringBuilder();
        String sender = null;
        long timestampMillis = 0;

        for (SmsMessage sms : messages) {
            if (sender == null) {
                sender = sms.getDisplayOriginatingAddress();
                timestampMillis = sms.getTimestampMillis();
            }
            bodyBuilder.append(sms.getDisplayMessageBody());
        }

        String body = bodyBuilder.toString().trim();
        if (body.isEmpty() || sender == null) return;

        Log.d(TAG, "SMS received from: " + sender + " | body: " + body.substring(0, Math.min(50, body.length())) + "...");

        // ── Path 1: Capacitor JS bridge (always attempted) ───────────────────
        // When the app is open/foregrounded, the WebView is alive and JS handles
        // the SMS entirely — deduplication + POST to backend all happen in JS.
        SmsPlugin.onSmsReceived(sender, body, timestampMillis);

        // ── Path 2: Native service fallback (only when JS is inactive) ───────
        // When the app is fully backgrounded or the WebView is destroyed,
        // the JS bridge cannot receive the event. In that case only, we use
        // the SmsListenerService to POST directly to the backend.
        // This mutual exclusion eliminates the duplicate POST problem.
        if (!SmsPlugin.isJsBridgeActive()) {
            Log.d(TAG, "JS bridge inactive — starting SmsListenerService as fallback");
            Intent serviceIntent = new Intent(context, SmsListenerService.class);
            serviceIntent.putExtra("sender", sender);
            serviceIntent.putExtra("body", body);
            serviceIntent.putExtra("timestamp", timestampMillis);
            ContextCompat.startForegroundService(context, serviceIntent);
        } else {
            Log.d(TAG, "JS bridge active — skipping SmsListenerService (JS will handle POST)");
        }
    }
}

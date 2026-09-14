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
 * Flow: SMS arrives → onReceive() → stores in SmsPlugin.lastSms →
 *       starts SmsListenerService if app is in background →
 *       service reads the SMS and POSTs to Jarvis backend.
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

        // Pass to the Capacitor plugin for JS-side processing
        // Store in SmsPlugin so the plugin can forward to JS
        SmsPlugin.onSmsReceived(sender, body, timestampMillis);

        // Also start the foreground service so Android doesn't kill us
        // before we finish posting to the backend
        Intent serviceIntent = new Intent(context, SmsListenerService.class);
        serviceIntent.putExtra("sender", sender);
        serviceIntent.putExtra("body", body);
        serviceIntent.putExtra("timestamp", timestampMillis);
        ContextCompat.startForegroundService(context, serviceIntent);
    }
}

package com.mangalgupta.jarvis;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * SmsListenerService — Foreground Service for Realme UI compatibility.
 *
 * Realme UI (ColorOS) is very aggressive about killing background apps.
 * Running as a foreground service shows a persistent notification and
 * prevents the OS from killing our SMS processing mid-request.
 *
 * This service receives SMS data from SmsReceiver and POSTs it to the
 * Jarvis backend (FastAPI) when the WebView JS bridge is not available
 * (e.g., app is completely backgrounded).
 */
public class SmsListenerService extends Service {

    private static final String TAG = "JarvisSmsService";
    private static final String CHANNEL_ID = "jarvis_sms_channel";
    private static final int NOTIFICATION_ID = 1001;

    // Configurable: your backend base URL
    // In production this should be your deployed API URL
    private static final String BACKEND_URL = "https://jarvis-gamma-ten.vercel.app";

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        startForeground(NOTIFICATION_ID, buildNotification("Monitoring payment SMS..."));
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String sender = intent.getStringExtra("sender");
            String body = intent.getStringExtra("body");
            long timestamp = intent.getLongExtra("timestamp", System.currentTimeMillis());

            if (body != null && !body.isEmpty()) {
                // Run network call on a background thread
                final String finalSender = sender != null ? sender : "";
                final String finalBody = body;
                final long finalTimestamp = timestamp;

                new Thread(() -> {
                    postSmsToBackend(finalSender, finalBody, finalTimestamp);
                    // Stop ourselves when done so we don't waste battery
                    stopSelf(startId);
                }).start();
            }
        }

        // START_NOT_STICKY: don't restart service if killed (SMS was already received)
        return START_NOT_STICKY;
    }

    private void postSmsToBackend(String sender, String body, long timestampMillis) {
        // Read JWT token from shared preferences (written by JS side after login)
        String token = getSharedPreferences("JarvisPrefs", MODE_PRIVATE)
                .getString("jwt_token", null);

        if (token == null) {
            Log.w(TAG, "No JWT token found — user may not be logged in. Skipping backend POST.");
            return;
        }

        String isoTimestamp = new java.util.Date(timestampMillis).toInstant().toString();

        try {
            JSONObject payload = new JSONObject();
            payload.put("sms_body", body);
            payload.put("sender", sender);
            payload.put("received_at", isoTimestamp);

            // Try the Node.js gateway first (same proxy pattern as web app)
            String endpoint = BACKEND_URL + "/api/expenses/sms";
            byte[] postData = payload.toString().getBytes(StandardCharsets.UTF_8);

            URL url = new URL(endpoint);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("Authorization", "Bearer " + token);
            conn.setRequestProperty("Content-Length", String.valueOf(postData.length));
            conn.setDoOutput(true);
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(10000);

            try (OutputStream os = conn.getOutputStream()) {
                os.write(postData);
            }

            int responseCode = conn.getResponseCode();
            if (responseCode == 200 || responseCode == 201) {
                Log.d(TAG, "✅ SMS expense posted to backend. Response: " + responseCode);
                // Update the foreground notification to confirm tracking
                updateNotification("✅ Expense auto-tracked from SMS");
            } else {
                Log.w(TAG, "Backend returned " + responseCode + " for SMS expense");
            }

            conn.disconnect();
        } catch (Exception e) {
            Log.e(TAG, "Failed to post SMS to backend: " + e.getMessage());
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Jarvis Payment Tracker",
                    NotificationManager.IMPORTANCE_LOW  // LOW = no sound, no popup
            );
            channel.setDescription("Tracks payment SMS for automatic expense logging");
            channel.setShowBadge(false);
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(channel);
        }
    }

    private Notification buildNotification(String text) {
        Intent launchIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, launchIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("Jarvis")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .build();
    }

    private void updateNotification(String text) {
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (nm != null) nm.notify(NOTIFICATION_ID, buildNotification(text));
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null; // Not a bound service
    }
}

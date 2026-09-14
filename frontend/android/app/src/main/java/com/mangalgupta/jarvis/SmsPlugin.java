package com.mangalgupta.jarvis;

import android.Manifest;
import android.content.ContentResolver;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.core.content.ContextCompat;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

/**
 * SmsPlugin — Capacitor plugin bridging native Android SMS to JavaScript.
 *
 * Exposed to JavaScript via:
 *   - SmsPlugin.checkPermissions()    → { read: 'granted'|'denied', receive: 'granted'|'denied' }
 *   - SmsPlugin.requestPermissions()  → same shape
 *   - SmsPlugin.readInbox(count)      → { messages: [{sender, body, timestamp}] }
 *   - SmsPlugin.addListener('onSmsReceived', callback)
 *
 * The static onSmsReceived(sender, body, ts) method is called by SmsReceiver
 * (the BroadcastReceiver) when a new SMS arrives.
 */
@CapacitorPlugin(
        name = "SmsPlugin",
        permissions = {
                @Permission(
                        alias = "readSms",
                        strings = { Manifest.permission.READ_SMS }
                ),
                @Permission(
                        alias = "receiveSms",
                        strings = { Manifest.permission.RECEIVE_SMS }
                ),
        }
)
public class SmsPlugin extends Plugin {

    private static final String TAG = "JarvisSmsPlugin";
    private static final String EVENT_SMS_RECEIVED = "onSmsReceived";

    // Static reference so SmsReceiver (BroadcastReceiver) can call us
    private static SmsPlugin instance;

    /**
     * True while the JS WebView has an active "onSmsReceived" listener.
     * SmsReceiver checks this to decide whether the JS bridge can handle
     * the SMS itself, or whether the native SmsListenerService fallback
     * is needed (app fully backgrounded / WebView not running).
     */
    private static boolean isJsBridgeActive = false;

    /** Call from SmsReceiver to check if JS is ready to handle the SMS. */
    public static boolean isJsBridgeActive() {
        return instance != null && isJsBridgeActive;
    }

    @Override
    public void load() {
        instance = this;
        Log.d(TAG, "SmsPlugin loaded and ready");
    }

    @Override
    protected void handleOnResume() {
        // WebView is visible and active — JS bridge is fully operational
        isJsBridgeActive = true;
        Log.d(TAG, "SmsPlugin: JS bridge is now ACTIVE (app foregrounded)");
    }

    @Override
    protected void handleOnPause() {
        // App went to background — JS bridge may become unavailable soon
        isJsBridgeActive = false;
        Log.d(TAG, "SmsPlugin: JS bridge is now INACTIVE (app backgrounded)");
    }

    /** Called by SmsReceiver when a new SMS arrives. */
    public static void onSmsReceived(String sender, String body, long timestampMillis) {
        if (instance == null) {
            Log.w(TAG, "Plugin not loaded yet — cannot fire JS event");
            return;
        }

        JSObject data = new JSObject();
        data.put("sender", sender);
        data.put("body", body);
        data.put("timestamp", new java.util.Date(timestampMillis).toInstant().toString());

        // Must post to main thread for Capacitor event emission
        new Handler(Looper.getMainLooper()).post(() -> {
            instance.notifyListeners(EVENT_SMS_RECEIVED, data);
            Log.d(TAG, "JS event fired: onSmsReceived from " + sender);
        });
    }

    /** Check if SMS permissions are already granted. */
    @PluginMethod
    public void checkPermissions(PluginCall call) {
        boolean canRead = ContextCompat.checkSelfPermission(
                getContext(), Manifest.permission.READ_SMS) == PackageManager.PERMISSION_GRANTED;
        boolean canReceive = ContextCompat.checkSelfPermission(
                getContext(), Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED;

        JSObject result = new JSObject();
        result.put("read", canRead ? "granted" : "denied");
        result.put("receive", canReceive ? "granted" : "denied");
        call.resolve(result);
    }

    /** Request READ_SMS and RECEIVE_SMS permissions. */
    @PluginMethod
    public void requestPermissions(PluginCall call) {
        if (ContextCompat.checkSelfPermission(getContext(), Manifest.permission.READ_SMS)
                == PackageManager.PERMISSION_GRANTED
                && ContextCompat.checkSelfPermission(getContext(), Manifest.permission.RECEIVE_SMS)
                == PackageManager.PERMISSION_GRANTED) {
            // Already granted
            JSObject result = new JSObject();
            result.put("read", "granted");
            result.put("receive", "granted");
            call.resolve(result);
            return;
        }
        requestPermissionForAliases(new String[]{"readSms", "receiveSms"}, call, "smsPermissionsCallback");
    }

    @PermissionCallback
    private void smsPermissionsCallback(PluginCall call) {
        boolean canRead = ContextCompat.checkSelfPermission(
                getContext(), Manifest.permission.READ_SMS) == PackageManager.PERMISSION_GRANTED;
        boolean canReceive = ContextCompat.checkSelfPermission(
                getContext(), Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED;

        JSObject result = new JSObject();
        result.put("read", canRead ? "granted" : "denied");
        result.put("receive", canReceive ? "granted" : "denied");
        call.resolve(result);
    }

    /**
     * Read recent SMS messages from the inbox.
     * Call: SmsPlugin.readInbox({ count: 50 })
     */
    @PluginMethod
    public void readInbox(PluginCall call) {
        if (ContextCompat.checkSelfPermission(getContext(), Manifest.permission.READ_SMS)
                != PackageManager.PERMISSION_GRANTED) {
            call.reject("READ_SMS permission not granted");
            return;
        }

        int count = call.getInt("count", 50);
        JSArray messages = new JSArray();

        try {
            ContentResolver cr = getContext().getContentResolver();
            Uri inboxUri = Uri.parse("content://sms/inbox");
            Cursor cursor = cr.query(
                    inboxUri,
                    new String[]{"address", "body", "date"},
                    null, null,
                    "date DESC LIMIT " + count
            );

            if (cursor != null) {
                while (cursor.moveToNext()) {
                    String sender = cursor.getString(cursor.getColumnIndexOrThrow("address"));
                    String body = cursor.getString(cursor.getColumnIndexOrThrow("body"));
                    long date = cursor.getLong(cursor.getColumnIndexOrThrow("date"));

                    JSObject msg = new JSObject();
                    msg.put("sender", sender);
                    msg.put("body", body);
                    msg.put("timestamp", new java.util.Date(date).toInstant().toString());
                    messages.put(msg);
                }
                cursor.close();
            }
        } catch (Exception e) {
            Log.e(TAG, "Error reading SMS inbox: " + e.getMessage());
            call.reject("Failed to read inbox: " + e.getMessage());
            return;
        }

        JSObject result = new JSObject();
        result.put("messages", messages);
        call.resolve(result);
    }
}

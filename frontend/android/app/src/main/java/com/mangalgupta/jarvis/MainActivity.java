package com.mangalgupta.jarvis;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // Register custom plugins BEFORE super.onCreate()
        registerPlugin(SmsPlugin.class);
        super.onCreate(savedInstanceState);
    }
}


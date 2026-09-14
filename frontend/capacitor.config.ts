import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.mangalgupta.jarvis',
  appName: 'Jarvis',
  // 'out' is where Next.js static export writes its files (next.config.ts: output: 'export')
  webDir: 'out',
  server: {
    // Use HTTPS scheme so cookies & localStorage work correctly in Android WebView
    androidScheme: 'https',
    // During development you can point to your live server instead:
    // url: 'http://192.168.x.x:3000',
    // cleartext: true,
  },
  android: {
    // Allow cleartext (HTTP) traffic to your local backend during development.
    // For production, switch your backend to HTTPS and remove this.
    allowMixedContent: true,
    // Realme / ColorOS: prevent WebView from being throttled in background
    // backgroundColor handles the splash while JS boots
    backgroundColor: '#0f172a',  // slate-950 matches dark mode bg
  },
  plugins: {
    // Push Notifications not needed for this app yet
    // SmsListener is a custom plugin — see android/app/src/main/java/...
    SplashScreen: {
      launchShowDuration: 1200,
      backgroundColor: '#0f172a',
      androidSplashResourceName: 'splash',
      showSpinner: false,
    },
  },
};

export default config;

export const getApiBaseUrl = (): string => {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  if (typeof window !== "undefined") {
    const origin = window.location.origin;
    const hostname = window.location.hostname;

    // Inside Android Capacitor WebView, origin/hostname is localhost/127.0.0.1/capacitor://
    const isCapacitorOrLocalhost =
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      origin.startsWith("capacitor://") ||
      typeof (window as any).Capacitor !== "undefined";

    if (isCapacitorOrLocalhost) {
      // Point directly to the live backend for Android app and mobile WebView
      return "https://jarvis-gamma-ten.vercel.app";
    }

    return origin;
  }

  return "https://jarvis-gamma-ten.vercel.app";
};

export const API_BASE_URL = getApiBaseUrl();

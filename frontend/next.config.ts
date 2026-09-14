import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["recharts"],
  // Enable static export for Capacitor Android APK build
  // The app runs in a WebView — no Node.js server on the phone
  output: "export",
  // next/image optimisation requires a server; disable for static export
  images: {
    unoptimized: true,
  },
};

export default nextConfig;

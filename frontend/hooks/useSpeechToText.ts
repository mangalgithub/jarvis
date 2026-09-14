"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/**
 * useSpeechToText
 *
 * Android (Capacitor WebView): uses @capacitor-community/speech-recognition
 *   which calls the native Android SpeechRecognizer — works without Chrome.
 *
 * Web (desktop Chrome / Safari): falls back to webkitSpeechRecognition.
 */

let CapacitorSpeechRecognition: any = null;

// Lazy-load the Capacitor plugin only in a browser/WebView environment
if (typeof window !== "undefined") {
  import("@capacitor-community/speech-recognition")
    .then((mod) => {
      CapacitorSpeechRecognition = mod.SpeechRecognition;
    })
    .catch(() => {
      // Plugin not available — will fall back to Web Speech API
    });
}

function isCapacitorNative(): boolean {
  return (
    typeof window !== "undefined" &&
    !!(window as any).Capacitor &&
    (window as any).Capacitor.isNativePlatform?.()
  );
}

export function useSpeechToText() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const webRecognitionRef = useRef<any>(null);

  // Initialize Web Speech API for non-native platforms
  useEffect(() => {
    if (isCapacitorNative()) return; // native platform — skip web init
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-IN"; // Better for Indian English & accents

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onresult = (event: any) => {
      const result = event.results[event.resultIndex];
      setTranscript(result[0].transcript);
    };
    recognition.onerror = (event: any) => {
      console.error("Web Speech error:", event.error);
      setIsListening(false);
    };

    webRecognitionRef.current = recognition;
  }, []);

  const startListening = useCallback(async () => {
    setTranscript("");

    if (isCapacitorNative() && CapacitorSpeechRecognition) {
      // ── Android Native path ──────────────────────────────────────────
      try {
        const { available } = await CapacitorSpeechRecognition.available();
        if (!available) {
          alert("Speech recognition is not available on this device.");
          return;
        }

        // Request microphone permission
        await CapacitorSpeechRecognition.requestPermissions();

        setIsListening(true);
        const result = await CapacitorSpeechRecognition.start({
          language: "en-IN",
          maxResults: 1,
          prompt: "Speak to Jarvis...",
          partialResults: false,
          popup: false,
        });

        if (result?.matches && result.matches.length > 0) {
          setTranscript(result.matches[0]);
        }
      } catch (err: any) {
        console.error("Capacitor speech recognition error:", err);
      } finally {
        setIsListening(false);
      }
    } else if (webRecognitionRef.current) {
      // ── Web Speech API fallback (desktop Chrome) ─────────────────────
      webRecognitionRef.current.start();
    } else {
      alert("Speech recognition is not supported in this browser.");
    }
  }, []);

  const stopListening = useCallback(async () => {
    if (isCapacitorNative() && CapacitorSpeechRecognition) {
      try {
        await CapacitorSpeechRecognition.stop();
      } catch {}
    } else if (webRecognitionRef.current) {
      webRecognitionRef.current.stop();
    }
    setIsListening(false);
  }, []);

  return {
    isListening,
    transcript,
    startListening,
    stopListening,
    setTranscript,
  };
}

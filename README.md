# Jarvis Personal OS 🤖
**The Ultimate AI-Powered Personal Operating System.**

Jarvis is a cutting-edge, multimodal AI assistant designed to manage your life with intelligence, context, and vision. Unlike generic chatbots, Jarvis remembers your preferences, tracks your physical health, manages your finances, and provides real-time market and news insights through a stunning glassmorphic dashboard.

---

## 👁️ Vision Intelligence (Multimodal)
- **AI Nutritionist:** Snap a photo of your food. Jarvis identifies the meal and automatically logs estimated calories and protein.
- **Smart Receipts:** Show Jarvis a shopping bill or restaurant receipt. He extracts the total and items to log your expenses instantly.
- **Visual Context:** Jarvis "sees" what you see, allowing for natural conversations about images.

## 🎙️ Voice & Sound
- **Hands-Free Control:** Integrated Speech-to-Text (STT) allows you to command Jarvis with your voice.
- **Audio Feedback:** Real-time visualizers and sound effects for a premium, interactive experience.

## 🧠 Contextual Memory & RAG
- **Deep Personalization:** Jarvis remembers your diet (e.g., "I am vegetarian"), your work habits, and your favorite topics.
- **Memory Audit:** A dedicated profile section where you can see exactly what Jarvis has learned about you.
- **Contextual Agency:** Every agent (Health, Finance, News) uses your memory to give better, personalized advice.

## 💰 Advanced Finance Agent
- **Natural Language Logging:** "Spent 500 on dinner at Pizza Hut" — Jarvis handles the rest.
- **Categorization:** Automatically sorts spending into Food, Travel, Bills, Shopping, etc.
- **Budgets & Goals:** Set monthly limits and track progress toward major savings goals.
- **Investment Insights:** Instant access to stock prices and mutual fund performance.

## 🏥 Health & Wellness Agent
- **Macro Tracking:** Precise logging of calories and protein with daily goal visualizations.
- **Hydration Tracker:** Interactive water logging to keep you hydrated throughout the day.
- **Workout Consistency:** Log your exercise sessions and track your weekly streaks.
- **Progress Charts:** High-performance Recharts integration for visual health trends.

## 📈 Real-time Market & News
- **Live Indices:** Real-time tracking of Nifty 50, Sensex, and global market trends.
- **Curated News:** AI-filtered news across Tech, World, and Markets.
- **AI Summarizer:** Jarvis can read and summarize any news article in seconds.

## ⚡ Technical Superpowers
- **Orchestrator Architecture:** A sophisticated brain that routes your requests to the specialized Health, Finance, News, or Stock agents.
- **Real-time Sync:** WebSockets ensure your dashboard updates instantly across all devices.
- **Multi-Cloud Deployment:** Powered by Vercel (Frontend/Backend) and Hugging Face (AI Core).

---

## 🛠️ Tech Stack
- **Frontend:** Next.js 15, Tailwind CSS, Framer Motion, HeroUI, Recharts.
- **Backend:** Node.js, Express, Socket.io, MongoDB Atlas.
- **AI Agents:** Python, FastAPI, LangChain, Gemini 2.5 Flash, Groq (Llama 3), Sentence-Transformers.

---

## 📦 Deployment Guide
1. **GitHub:** Connect your repo to Vercel for the Frontend/Backend.
2. **Hugging Face:** Create a Docker Space for the `agents/` folder.
3. **Environment:** Ensure `GOOGLE_API_KEY`, `GROQ_API_KEY`, and `MONGODB_URI` are set in the cloud variables.

---
*Created with ❤️ by Mangal Gupta.*
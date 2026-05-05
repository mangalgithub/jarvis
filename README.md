# Jarvis Personal OS 🤖
**The Ultimate Production-Grade Personal AI Operating System.**

Jarvis is a sophisticated, multimodal AI assistant designed to manage your life with high-fidelity intelligence, deterministic accuracy, and stateful memory. Jarvis moves beyond simple chat and implements complex multi-turn agency, robust logic-NLP decoupling, and real-time situational awareness.

---

## 🏥 High-Fidelity Health OS (V4) 🏆
Jarvis implements an elite health tracking pipeline that prioritizes accuracy and interactive reliability.
- **Deterministic Math Engine:** Moves away from LLM-based "guessing." NLP is used only for entity extraction, while a pure Python backend handles all mathematical computations using a curated Food Database.
- **Priority Entity Matching:** Implements "Longest-Match-First" logic to ensure composite dishes (e.g., "Chicken Curry") are matched before raw ingredients ("Chicken"), preventing protein overestimation.
- **Interactive Clarification Loop:** Jarvis identifies vague inputs (e.g., "I had some chicken") and pauses the log to ask for clarification, ensuring 100% data integrity.
- **Context-Aware Multipliers:** Automatically detects preparation context (Restaurant vs. Home) and applies caloric multipliers for hidden fats/oils.
- **Protein Density Guardrails:** Built-in sanity checks that flag physically impossible macro claims (e.g., >35% protein density in cooked meals).

## 🧠 Contextual Memory & Stateful Session Management
- **Short-Term Session State:** Powered by a MongoDB-backed `ConversationStateService`, Jarvis can "remember" pending actions across multiple turns.
- **Message Re-Hydration:** Jarvis "stitches" user answers back into original commands (e.g., *"I had some chicken"* + *"1 bowl"* → *"I had 1 bowl of chicken"*).
- **Temporal Awareness:** Real-time clock injection ensures Jarvis knows the time and date, providing situational greetings and accurate log timestamps.
- **Deep RAG Integration:** Long-term memory storage of user preferences, habits, and constraints for personalized advice.

## 👁️ Vision Intelligence (Multimodal)
- **AI Nutritionist:** Snap a photo of your food. Jarvis identifies the meal and automatically logs deterministic calories and protein.
- **Smart Receipts:** Show Jarvis a shopping bill or restaurant receipt. He extracts the total and items to log your expenses instantly.
- **Visual Context:** Jarvis "sees" what you see, allowing for natural conversations about images.

## 💰 Advanced Finance Agent
- **Natural Language Logging:** "Spent 500 on dinner at Pizza Hut" — Jarvis handles the rest.
- **Categorization:** Automatically sorts spending into Food, Travel, Bills, Shopping, etc.
- **Budgets & Goals:** Set monthly limits and track progress toward major savings goals.

## ⚡ Technical Superpowers
- **Multi-Agent Orchestrator:** A central brain that handles intent classification and routes requests to specialized agents (Health, Finance, News, etc.).
- **Logic-NLP Decoupling:** Core architectural pattern that uses LLMs for understanding and pure code for execution, ensuring zero-hallucination math.
- **Real-time Sync:** WebSockets ensure your dashboard updates instantly across all devices.

---

## 🛠️ Tech Stack
- **Frontend:** Next.js 15, Tailwind CSS, Framer Motion, HeroUI, Recharts.
- **Backend:** Node.js, Express, Socket.io, MongoDB Atlas.
- **AI Core:** Python, FastAPI, Groq (Llama 3), Gemini 2.0 Flash, MongoDB.
- **Infrastructure:** Vercel (Web), Hugging Face (Dockerized Agents).

---

## 📦 Deployment Guide
1. **GitHub:** Connect your repo to Vercel for the Frontend/Backend.
2. **Hugging Face:** Create a Docker Space for the `agents/` folder.
3. **Environment:** Ensure `GOOGLE_API_KEY`, `GROQ_API_KEY`, and `MONGODB_URI` are set.

---
*Created with ❤️ by Mangal Gupta.*
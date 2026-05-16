# Jarvis Personal AI Operating System

A scalable, production-grade Multi-Agent AI Assistant designed to unify personal finance, health tracking, market research, and daily scheduling through a multimodal conversational interface. 

Built to address application fragmentation, Jarvis implements complex multi-turn agency, strict logic-NLP decoupling, real-time WebSocket communication, and stateful memory management. It serves as a comprehensive showcase of modern backend architecture, concurrent processing, and generative AI engineering.

---

## System Architecture & Key Engineering Features

1. **Multi-Agent Orchestration Engine**  
   A central routing layer classifies user intents and seamlessly delegates commands to isolated, specialized agents (Finance, Health, Stock, News, Memory, Reminders).

2. **Deterministic AI (Logic-NLP Decoupling)**  
   To eliminate mathematical hallucinations common in Large Language Models, Jarvis utilizes LLMs strictly as NLP parsers for entity extraction. A robust Python backend handles all mathematical computations, boundary checks, and database transactions, ensuring 100% data integrity.

3. **Multimodal Vision Automation**  
   Integrates vision models for automated data entry. Users can upload images of restaurant receipts or meals; the system extracts the merchant name, total amounts, or nutritional estimates and automatically routes the payload to the corresponding database via the appropriate agent.

4. **Monthly AI Analytics Pipeline**  
   Aggregates financial data across defined temporal boundaries, compares actual spending against dynamically set budgets, and leverages generative AI to synthesize personalized financial advisory reports.

5. **High-Performance Infrastructure**  
   - **Distributed Caching (Redis):** External API requests (e.g., Yahoo Finance, NewsAPI) are cached in Redis, mitigating rate limits and reducing widget load times to `<50ms`.
   - **Concurrent Processing:** Implements asynchronous execution (`asyncio.gather`) to parallelize dashboard data fetching, avoiding sequential blocking.
   - **Database Optimization:** Utilizes MongoDB Compound Indexes to ensure O(log N) query performance across large datasets.

6. **Real-Time WebSockets & Background Schedulers**  
   A background cron scheduler polls the database every 10 seconds, pushing live reminders and state updates to the Next.js frontend via a custom WebSocket Connection Manager featuring automated stale connection cleanup.

---

## Core Capabilities

### Finance Agent
- **Natural Language Parsing:** Automatically categorizes expenses, identifies payment methods, and handles database insertions from unstructured text (e.g., *"Spent ₹500 on dinner at Pizza Hut"*).
- **Budget Tracking:** Monitors monthly limits and tracks progress toward user-defined savings goals.

### High-Fidelity Health OS
- **Priority Entity Matching:** Implements longest-match-first logic to ensure composite dishes are matched accurately before raw ingredients, preventing macronutrient overestimation.
- **Stateful Clarification Loop:** Identifies vague inputs, pauses database insertion, and manages session state in MongoDB to prompt the user for exact portion sizes before proceeding.
- **Context-Aware Multipliers:** Detects preparation context (e.g., restaurant dining) to dynamically adjust caloric estimates for hidden fats and oils.

### Market & News Intelligence
- **Live Market Data:** Fetches and caches live equity quotes and mutual fund NAVs.
- **LLM Summarization:** Aggregates global headlines and synthesizes cohesive, multi-sentence executive briefings.

---

## Technology Stack

- **Frontend:** Next.js 15, React, Tailwind CSS, HeroUI, Framer Motion, Recharts.
- **Backend Core:** Python, FastAPI, WebSockets (`asyncio`), Redis (Upstash).
- **AI Models:** Groq (Llama 3 70B for high-speed NLP parsing), Google Gemini 2.5 (Vision AI & Fallbacks).
- **Database:** MongoDB Atlas (NoSQL Document Store with Compound Indexing).
- **Infrastructure & Deployment:** Vercel (Frontend), Hugging Face Spaces (Dockerized Python Agents).

---

## Local Setup & Deployment

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   ```

2. **Frontend Initialization:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Backend Agent Initialization:**
   ```bash
   cd agents
   python -m venv .venv
   source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

4. **Environment Configuration:**
   Create a `.env` file in the `agents/` directory containing required API keys:
   `GROQ_API_KEY`, `GOOGLE_API_KEY`, `MONGODB_URI`, `REDIS_URL`, and `NEWS_API_KEY`.
# Jarvis Personal OS 🤖

Jarvis is a powerful, multi-cloud personal operating system designed to be your ultimate AI assistant. It integrates finance tracking, health monitoring, real-time news briefings, and market insights into a beautiful, unified dashboard accessible from any device.

## 🚀 Live Demo
- **Frontend/Backend:** Deployed on [Vercel](https://vercel.com)
- **AI Agents:** Deployed on [Hugging Face Spaces](https://huggingface.co/spaces) (Docker)

## ✨ Features

### 💬 Intelligence & Memory
- **Proactive AI:** Jarvis learns about your preferences, habits, and goals.
- **Contextual Memory:** Remembers personal details (diet, work, preferences) to provide tailored advice.
- **Voice Interaction:** Native Speech-to-Text for hands-free commands.

### 💰 Finance Management
- **Automatic Logging:** Log expenses via natural language (e.g., "Spent 500 on dinner").
- **Budget Tracking:** Set monthly limits and get real-time progress bars.
- **Visual Analytics:** 7-day spending trends and category-wise breakdowns.

### 🏥 Health & Wellness
- **Hydration Tracking:** Monitor water intake against daily goals.
- **Nutrition:** Log calories and protein to maintain your fitness streak.
- **Workout Insights:** Tracks your exercise consistency and last activity.

### 📰 Daily Briefings
- **Curated News:** Real-time briefings across India, World, and AI categories.
- **AI Summaries:** Ask Jarvis to summarize complex articles for you.

### 📈 Market Insights
- **Live Indices:** Track Nifty 50 and other global markets.
- **Stock Tracking:** Get instant updates on stock prices and performance.

---

## 🛠️ Tech Stack

- **Frontend:** Next.js 15, Tailwind CSS, Framer Motion, HeroUI
- **Backend:** Node.js (Express), WebSocket for real-time notifications
- **AI Service:** Python (FastAPI), LangChain, Sentence-Transformers
- **Database:** MongoDB Atlas
- **Infrastructure:** Multi-cloud (Vercel + Hugging Face)

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- Node.js (v18+)
- Python 3.10+
- MongoDB Atlas Account
- Hugging Face Account

### 2. Environment Variables

Create `.env` files in the respective directories:

**Root / Backend:**
```env
MONGODB_URI=your_mongodb_atlas_uri
SECRET_KEY=your_jwt_secret
AGENT_SERVICE_URL=https://your-hf-space-url.hf.space
```

**Frontend:**
```env
NEXT_PUBLIC_API_BASE_URL=https://your-vercel-domain.com
```

**Agents (Python):**
```env
MONGODB_URI=your_mongodb_atlas_uri
SECRET_KEY=your_jwt_secret
HF_TOKEN=your_huggingface_token
```

### 3. Running Locally

**Start the Backend:**
```bash
cd backend
npm install
npm run dev
```

**Start the Agents:**
```bash
cd agents
pip install -r requirements.txt
uvicorn main:app --reload
```

**Start the Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## 📦 Deployment

### Vercel (Frontend & Backend)
The project includes a `vercel.json` for multi-service deployment.
1. Connect your GitHub repo to Vercel.
2. Set the Environment Variables in the Vercel Dashboard.
3. Deploy!

### Hugging Face (AI Agents)
1. Create a new Docker Space on Hugging Face.
2. Upload the `agents/` directory.
3. Hugging Face will automatically build and deploy using the provided `Dockerfile`.

---

## 📜 License
MIT License. Created by Mangal Gupta.

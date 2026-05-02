# Jarvis Personal OS 🤖

Jarvis is a powerful, multi-cloud personal operating system designed to be your ultimate AI assistant. It integrates finance tracking, health monitoring, real-time news briefings, and market insights into a beautiful, unified dashboard accessible from any device.

## 🚀 Live Demo
- **Frontend/Backend:** Deployed on [Vercel](https://vercel.com)
- **AI Agents:** Deployed on [Hugging Face Spaces](https://huggingface.co/spaces) (Docker)

## ✨ Features

### 💬 Intelligence & Memory
- **Proactive AI:** Jarvis learns about your preferences, habits, and goals through natural conversation.
- **Contextual Memory:** Remembers personal details (diet, work, preferences) to provide tailored advice.
- **Morning Briefing:** Get a personalized summary of your day, including weather, news, and tasks.
- **Voice Interaction:** Native Speech-to-Text for hands-free commands.
- **Memory Audit:** View and manage everything Jarvis knows about you in the Profile section.

### 💰 Finance Management
- **Natural Language Logging:** Log expenses like "I spent 500 on coffee at Starbucks".
- **Intelligent Categorization:** Automatically assigns categories to your spending.
- **Budget Monitoring:** Set monthly budgets for specific categories and track progress.
- **Investment Insights:** Ask for mutual fund NAVs or stock prices instantly.
- **Savings Goals:** Track progress toward major purchases or financial milestones.

### 🏥 Health & Wellness
- **Water Tracker:** Log glasses of water and visualize your daily hydration goal.
- **Macro Tracking:** Log calorie and protein intake to stay on top of your fitness goals.
- **Workout Logs:** Keep track of your gym sessions and workout consistency.
- **Health Trends:** Visualize your health data over time with integrated charts.

### 📰 Daily Briefings
- **Curated News:** Stay updated with news from India, the World, and the AI industry.
- **AI Summary Engine:** Jarvis can read and summarize long articles so you don't have to.
- **Category Tabs:** Switch between different news interests effortlessly.

### 📈 Market Insights
- **Live Market Tracking:** Real-time data for major indices like Nifty 50 and Sensex.
- **Portfolio Monitoring:** Ask Jarvis about your stock performance or current prices.
- **Market News:** Get the latest news specifically related to financial markets.

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
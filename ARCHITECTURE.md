# Jarvis Architecture

Jarvis is split into three main parts:

- `backend/`: Node.js Express API for app routes, auth, dashboard data, and calling the Python agent service.
- `agents/`: Python FastAPI service for orchestration, multi-agent workflows, tools, and AI logic.
- `frontend/`: Next.js dashboard and chat UI.

## Runtime Flow

```txt
Frontend dashboard/chat
  -> Node.js backend
  -> Python agent service
  -> Orchestrator
  -> Specialist agents
  -> Tools, APIs, memory, database
```

## Main Agent Roles

- Orchestrator: routes user requests to the right agents.
- Memory agent: stores personal preferences, goals, and context.
- News agent: fetches and summarizes national, international, AI, and tech news.
- Finance agent: tracks expenses and generates spending summaries.
- Stock agent: analyzes stocks, mutual funds, and market trends.
- Health agent: tracks workouts, calories, protein, water, and plans.
- Learning agent: suggests AI/tech videos, courses, and roadmaps.
- Reminder agent: schedules water, workout, news, and monthly report reminders.

## Next Build Steps

1. Install and run the Python FastAPI agent service.
2. Run the Node backend and connect `/api/chat` to `/agent/chat`.
3. Build the frontend dashboard around `/api/chat` and `/api/dashboard`.
4. Implement the finance agent first because it establishes memory, database writes, and charts.
5. Add news, health, learning, stocks, voice, and notifications in that order.

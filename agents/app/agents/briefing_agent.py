"""
Briefing Agent: Generates 'Today with Jarvis' Proactive Daily Briefing.

Combines deterministic calculations (spending pace, month-end forecast,
health goal progress, upcoming bills & reminders) with AI synthesis
to generate concrete, high-impact suggestions and conversational audio script.
"""

import asyncio
import calendar
import json
import logging
import re
from datetime import datetime, timedelta, timezone

from app.agents.health_agent import HealthAgent
from app.agents.news_agent import NewsAgent
from app.agents.stock_agent import StockAgent
from app.core.llm import LLMUnavailableError, generate_response
from app.core.mongodb import get_collection
from app.tools.finance_tools import month_bounds, now_local
from app.tools.reminder_tools import get_active_reminders
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

health_agent = HealthAgent()
news_agent = NewsAgent()
stock_agent = StockAgent()


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


class BriefingAction(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=280)
    category: str = "finance"
    action_command: str | None = Field(default=None, max_length=240)


class BriefingSynthesis(BaseModel):
    greeting: str = Field(min_length=1, max_length=120)
    headline: str = Field(min_length=1, max_length=280)
    suggested_actions: list[BriefingAction] = Field(min_length=1, max_length=3)
    audio_script: str = Field(min_length=1, max_length=1200)


class BriefingAgent:
    name = "briefing"

    async def run(self, context: dict) -> dict:
        """Executes daily briefing when invoked via chat orchestrator."""
        user_id = context.get("user_id", "default-user")
        data = await self.get_briefing_data(user_id=user_id)

        actions_list = data.get("suggested_actions", [])
        actions_text = "\n".join(
            f"• **{a['title']}**: {a['description']}" for a in actions_list
        )

        pace = data["finance_pace"]
        health = data["health_progress"]
        water = health["water"]

        reply = (
            f"🌅 **{data['greeting']}**\n\n"
            f"{data['headline']}\n\n"
            f"📊 **Financial Pace (Day {pace['day_of_month']}/{pace['total_days']}):**\n"
            f"• Month Spend: ₹{pace['month_spent']:,.0f} | Burn Rate: ₹{pace['daily_burn_rate']:,.0f}/day\n"
            f"• Forecasted Month-End: ₹{pace['forecast_month_end']:,.0f}"
            + (f" *(Budget: ₹{pace['total_budget']:,.0f})*" if pace['total_budget'] > 0 else "") + "\n\n"
            f"💧 **Health & Priorities:**\n"
            f"• Hydration: {water.get('today', 0)} / {water.get('goal', 8)} glasses\n"
            f"• Workout Streak: {health.get('workout_streak', 0)} days\n\n"
            f"💡 **Suggested Focus Today:**\n{actions_text}"
        )

        return {
            "reply": reply,
            "actions": [{"type": "daily_briefing", "briefing": data}],
        }

    async def get_briefing_data(self, user_id: str, user_name: str = "User") -> dict:
        """
        Gathers all deterministic metrics across finance, health,
        reminders, and markets, then synthesizes with Groq.
        """
        now = now_local()
        year = now.year
        month = now.month
        day = now.day
        total_days_in_month = calendar.monthrange(year, month)[1]
        days_remaining = total_days_in_month - day
        month_start, month_end = month_bounds(now)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        # ── 1. Gather raw data concurrently ───────────────────────────────────
        (
            today_expenses_doc,
            month_expenses_doc,
            month_income_doc,
            budgets_docs,
            category_expenses_docs,
            recurring_docs,
            reminders_docs,
            health_summary,
            stocks_data,
            news_data,
        ) = await asyncio.gather(
            # Today expenses
            get_collection("expenses").aggregate([
                {"$match": {
                    "user_id": user_id,
                    "$or": [
                        {"occurred_at": {"$gte": today_start, "$lte": today_end}},
                        {"occurred_at": {"$exists": False}, "created_at": {"$gte": today_start, "$lte": today_end}},
                    ]
                }},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]).to_list(length=1),

            # Month expenses
            get_collection("expenses").aggregate([
                {"$match": {
                    "user_id": user_id,
                    "$or": [
                        {"occurred_at": {"$gte": month_start, "$lte": month_end}},
                        {"occurred_at": {"$exists": False}, "created_at": {"$gte": month_start, "$lte": month_end}},
                    ]
                }},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]).to_list(length=1),

            # Month income
            get_collection("income").aggregate([
                {"$match": {
                    "user_id": user_id,
                    "occurred_at": {"$gte": month_start, "$lte": month_end}
                }},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]).to_list(length=1),

            # Budgets
            get_collection("budgets").find({"user_id": user_id}).to_list(length=50),

            # One grouped query replaces one database query per budget category.
            get_collection("expenses").aggregate([
                {"$match": {
                    "user_id": user_id,
                    "$or": [
                        {"occurred_at": {"$gte": month_start, "$lte": month_end}},
                        {"occurred_at": {"$exists": False}, "created_at": {"$gte": month_start, "$lte": month_end}},
                    ]
                }},
                {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
            ]).to_list(length=100),

            # Recurring expenses
            get_collection("recurring_expenses").find({"user_id": user_id}).to_list(length=20),

            # Reminders
            get_active_reminders(user_id),

            # Health
            self._safe_health(user_id),

            # Stocks
            self._safe_stocks(),

            # News
            self._safe_news(),
        )

        today_spent = today_expenses_doc[0]["total"] if today_expenses_doc else 0.0
        month_spent = month_expenses_doc[0]["total"] if month_expenses_doc else 0.0
        month_income = month_income_doc[0]["total"] if month_income_doc else 0.0

        # ── 2. Deterministic Financial Pace & Forecast Math ──────────────────
        daily_burn_rate = round(month_spent / max(day, 1), 2)
        forecast_month_end = round(daily_burn_rate * total_days_in_month, 2)
        total_monthly_budget = sum(b.get("amount", 0) for b in budgets_docs)
        budget_variance = round(total_monthly_budget - forecast_month_end, 2) if total_monthly_budget > 0 else 0.0
        is_over_budget_projected = forecast_month_end > total_monthly_budget if total_monthly_budget > 0 else False

        # Budget category warnings
        budget_warnings = []
        category_spend = {
            row.get("_id"): float(row.get("total", 0))
            for row in category_expenses_docs
        }
        for b in budgets_docs:
            cat = b.get("category", "Other")
            cat_budget = b.get("amount", 0)
            if cat_budget > 0:
                cat_spent = category_spend.get(cat, 0.0)
                cat_forecast = round((cat_spent / max(day, 1)) * total_days_in_month, 2)
                if cat_forecast > cat_budget:
                    budget_warnings.append({
                        "category": cat,
                        "budget": cat_budget,
                        "spent": cat_spent,
                        "forecast": cat_forecast,
                        "overage": round(cat_forecast - cat_budget, 2),
                    })

        # ── 3. Deterministic Health Progress ─────────────────────────────────
        water_data = health_summary.get("water", {"today": 0, "goal": 8, "progress": 0}) if health_summary else {"today": 0, "goal": 8, "progress": 0}
        nutrition_data = health_summary.get("nutrition", {}) if health_summary else {}
        calories_data = nutrition_data.get("calories", {"today": 0, "goal": 2000})
        protein_data = nutrition_data.get("protein", {"today": 0, "goal": 120})
        workout_data = health_summary.get("workout", {"streak_days": 0}) if health_summary else {"streak_days": 0}

        # ── 4. Deterministic Upcoming Bills & Reminders ──────────────────────
        recurring_bills = [
            {"description": r.get("description", "Bill"), "amount": r.get("amount", 0), "category": r.get("category", "Bills")}
            for r in recurring_docs
        ]
        reminders_list = [
            {"_id": str(rem.get("_id", "")), "task": rem.get("task", ""), "execute_at": rem.get("execute_at", "")}
            for rem in reminders_docs[:5]
        ]

        # ── 5. Market / News Snapshot ────────────────────────────────────────
        nifty_info = next((s for s in stocks_data.get("indices", []) if "Nifty" in s.get("name", "")), None)
        news_highlight = None
        if news_data:
            first_cat = next(iter(news_data.values()), None)
            if first_cat and first_cat.get("articles"):
                first_art = first_cat["articles"][0]
                news_highlight = {"title": first_art.get("title", ""), "source": first_art.get("source", "")}

        # ── 6. Groq AI Synthesis (1–3 Concrete Actions + Audio Script) ───────
        greeting_time = "morning" if now.hour < 12 else ("afternoon" if now.hour < 17 else "evening")
        ai_synthesis = await self._synthesize_briefing(
            user_name=user_name,
            greeting_time=greeting_time,
            day_of_month=day,
            total_days=total_days_in_month,
            days_remaining=days_remaining,
            month_spent=month_spent,
            daily_burn_rate=daily_burn_rate,
            forecast_month_end=forecast_month_end,
            total_monthly_budget=total_monthly_budget,
            budget_warnings=budget_warnings,
            water_data=water_data,
            calories_data=calories_data,
            protein_data=protein_data,
            workout_streak=workout_data.get("streak_days", 0),
            reminders_count=len(reminders_list),
            recurring_count=len(recurring_bills),
            nifty_info=nifty_info,
        )

        return {
            "date_key": now.strftime("%Y-%m-%d"),
            "date": now.strftime("%A, %B %d, %Y"),
            "greeting": ai_synthesis.get("greeting", f"Good {greeting_time}, {user_name}!"),
            "headline": ai_synthesis.get("headline", f"Here is your daily overview for day {day} of {total_days_in_month}."),
            "audio_script": ai_synthesis.get("audio_script", ""),
            "suggested_actions": ai_synthesis.get("suggested_actions", []),
            "finance_pace": {
                "day_of_month": day,
                "total_days": total_days_in_month,
                "days_remaining": days_remaining,
                "today_spent": today_spent,
                "month_spent": month_spent,
                "daily_burn_rate": daily_burn_rate,
                "forecast_month_end": forecast_month_end,
                "total_budget": total_monthly_budget,
                "budget_variance": budget_variance,
                "is_over_budget_projected": is_over_budget_projected,
                "budget_warnings": budget_warnings,
            },
            "health_progress": {
                "water": water_data,
                "calories": calories_data,
                "protein": protein_data,
                "workout_streak": workout_data.get("streak_days", 0),
            },
            "schedule_alerts": {
                "reminders": reminders_list,
                "recurring_bills": recurring_bills[:3],
                "reminders_count": len(reminders_list),
            },
            "market_news": {
                "market": nifty_info,
                "news": news_highlight,
            },
        }

    async def _synthesize_briefing(self, **kwargs) -> dict:
        prompt = f"""You are Jarvis, an ultra-smart personal executive AI.
Synthesize this user's daily data into a crisp, high-impact Daily Briefing JSON.

DATA:
- User Name: {kwargs.get('user_name')}
- Greeting Time: {kwargs.get('greeting_time')}
- Day: {kwargs.get('day_of_month')} of {kwargs.get('total_days')} ({kwargs.get('days_remaining')} days remaining)
- Month Spend so far: ₹{kwargs.get('month_spent')}
- Current Daily Burn Rate: ₹{kwargs.get('daily_burn_rate')}/day
- Forecasted Month-End Spend: ₹{kwargs.get('forecast_month_end')}
- Total Monthly Budget: ₹{kwargs.get('total_monthly_budget')}
- Category Budget Warnings: {kwargs.get('budget_warnings')}
- Health Water: {kwargs.get('water_data')} glasses
- Health Calories: {kwargs.get('calories_data')}
- Health Protein: {kwargs.get('protein_data')}
- Workout Streak: {kwargs.get('workout_streak')} days
- Active Reminders: {kwargs.get('reminders_count')}
- Upcoming Recurring Bills: {kwargs.get('recurring_count')}
- Nifty 50: {kwargs.get('nifty_info')}

REQUIREMENTS:
1. "greeting": Dynamic greeting like "Good morning, Mangal!"
2. "headline": 1 punchy, motivating sentence summarizing today's key financial or health focus.
3. "suggested_actions": Array of 1 to 3 concrete, specific, high-impact actions. Each action must have:
   - "title": Short title (e.g., "Cap Dining Delivery", "Hydration Boost", "Review Reminders")
   - "description": Concrete advice with numbers (e.g., "You're on track to exceed food budget by ₹1,800—cook tonight or cap delivery.")
   - "category": "finance" | "health" | "schedule" | "market"
   - "action_command": Optional prefilled Jarvis command like "Drank 2 glasses of water" or "Show food budget"
4. "audio_script": A 30-second conversational voice summary for TTS read-aloud (energetic, polished, natural Jarvis tone).

Return ONLY valid JSON matching this structure:
{{
  "greeting": "...",
  "headline": "...",
  "suggested_actions": [
    {{
      "title": "...",
      "description": "...",
      "category": "finance",
      "action_command": "..."
    }}
  ],
  "audio_script": "..."
}}
"""
        try:
            response = await generate_response(
                prompt,
                system_prompt="You generate personal AI daily briefings. Return strict JSON only.",
                temperature=0.2,
            )
            data = _parse_json(response)
            if data:
                return BriefingSynthesis.model_validate(data).model_dump()
        except Exception as exc:
            logger.warning("[BriefingAgent] AI synthesis failed: %s", exc)

        # Graceful fallback
        name = kwargs.get("user_name", "User")
        time_str = kwargs.get("greeting_time", "morning")
        burn = kwargs.get("daily_burn_rate", 0)
        forecast = kwargs.get("forecast_month_end", 0)

        return {
            "greeting": f"Good {time_str}, {name}!",
            "headline": f"Your current spending pace is ₹{burn:,.0f}/day, putting month-end at ~₹{forecast:,.0f}.",
            "suggested_actions": [
                {
                    "title": "Monitor Spending Pace",
                    "description": f"Daily average is ₹{burn:,.0f}. Keep daily spends under control to stay on budget.",
                    "category": "finance",
                    "action_command": "Show my expenses this week",
                },
                {
                    "title": "Stay Hydrated",
                    "description": "Log your water intake throughout the day to hit your hydration target.",
                    "category": "health",
                    "action_command": "Drank 2 glasses of water",
                },
            ],
            "audio_script": f"Good {time_str}, {name}. Your daily briefing is ready. Your average burn rate is ₹{burn:,.0f} per day. Stay focused on your budget and health goals today.",
        }

    async def _safe_health(self, user_id: str) -> dict | None:
        try:
            return await health_agent.get_dashboard_health(user_id)
        except Exception:
            return None

    async def _safe_stocks(self) -> dict:
        try:
            return await stock_agent.get_dashboard_stocks()
        except Exception:
            return {"indices": []}

    async def _safe_news(self) -> dict | None:
        try:
            return await news_agent.get_dashboard_news(["india", "world", "ai"])
        except Exception:
            return None

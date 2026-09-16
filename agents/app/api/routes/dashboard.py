import asyncio
import logging
from datetime import datetime, timezone

from bson import ObjectId

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import verify_token
from app.core.redis import cache_get, cache_set

from app.agents.health_agent import HealthAgent
from app.agents.news_agent import NewsAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.stock_agent import StockAgent
from app.agents.sms_expense_agent import SmsExpenseAgent
from app.agents.briefing_agent import BriefingAgent
from app.tools.reminder_tools import get_active_reminders
from app.core.mongodb import get_collection
from app.tools.finance_tools import month_bounds, now_local, resolve_date_range

router = APIRouter()
news_agent = NewsAgent()
health_agent = HealthAgent()
memory_agent = MemoryAgent()
stock_agent = StockAgent()
sms_expense_agent = SmsExpenseAgent()
briefing_agent = BriefingAgent()

logger = logging.getLogger(__name__)


# ─── Pydantic model for SMS ingestion ─────────────────────────────────────────
class SmsExpenseRequest(BaseModel):
    sms_body: str
    sender: str = ""
    received_at: str | None = None  # ISO 8601 string from Android

DASHBOARD_CACHE_TTL = 45  # seconds


def serialize_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value) if value.__class__.__name__ == "ObjectId" else value


def serialize_document(document: dict):
    return {key: serialize_value(value) for key, value in document.items()}


def expense_match(user_id: str, start, end, category: str | None = None):
    match = {"user_id": user_id}

    if start is not None:
        match["$or"] = [
            {"occurred_at": {"$gte": start, "$lte": end}},
            {
                "occurred_at": {"$exists": False},
                "created_at": {"$gte": start, "$lte": end},
            },
        ]

    if category and category != "All":
        match["category"] = category

    return match


async def expense_total(user_id: str, start, end, category: str | None = None):
    pipeline = [
        {"$match": expense_match(user_id, start, end, category)},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    result = await get_collection("expenses").aggregate(pipeline).to_list(length=1)
    return result[0]["total"] if result else 0


async def income_total(user_id: str, start, end):
    pipeline = [
        {
            "$match": {
                "user_id": user_id,
                "occurred_at": {"$gte": start, "$lte": end},
            }
        },
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    result = await get_collection("income").aggregate(pipeline).to_list(length=1)
    return result[0]["total"] if result else 0


async def category_breakdown(user_id: str, start, end, category: str | None = None):
    pipeline = [
        {"$match": expense_match(user_id, start, end, category)},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
        {"$sort": {"total": -1}},
    ]
    rows = await get_collection("expenses").aggregate(pipeline).to_list(length=20)
    return [
        {"category": row["_id"] or "Other", "total": row["total"]}
        for row in rows
    ]


async def recent_expenses(user_id: str, start, end, category: str | None = None):
    documents = await get_collection("expenses").find(
        expense_match(user_id, start, end, category)
    ).sort([("occurred_at", -1), ("created_at", -1), ("_id", -1)]).to_list(length=15)
    return [serialize_document(document) for document in documents]


async def budget_status(user_id: str, month_start, month_end):
    budgets = await get_collection("budgets").find({"user_id": user_id}).to_list(length=50)
    results = []

    for budget in budgets:
        spent = await expense_total(
            user_id,
            month_start,
            month_end,
            category=budget.get("category"),
        )
        amount = budget.get("amount", 0)
        results.append(
            {
                "category": budget.get("category", "Other"),
                "budget": amount,
                "spent": spent,
                "remaining": amount - spent,
                "period": budget.get("period", "monthly"),
                "progress": min(round((spent / amount) * 100, 1), 999) if amount else 0,
            }
        )

    return results


async def savings_goals(user_id: str):
    documents = await get_collection("savings_goals").find(
        {"user_id": user_id}
    ).sort("created_at", -1).to_list(length=20)
    return [serialize_document(document) for document in documents]


async def recurring_expenses(user_id: str):
    documents = await get_collection("recurring_expenses").find(
        {"user_id": user_id}
    ).sort("created_at", -1).to_list(length=20)
    serialized = [serialize_document(document) for document in documents]
    total = sum(item.get("amount", 0) for item in serialized)
    return {"items": serialized, "total": total}


async def finance_trends(user_id: str):
    import datetime
    now = now_local()
    trends = []
    for i in range(6, -1, -1):
        day = now - datetime.timedelta(days=i)
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        total = await expense_total(user_id, start, end)
        trends.append({
            "date": day.strftime("%b %d"),
            "amount": total
        })
    return trends


# ── Safe wrappers for concurrent dashboard fetches ──────────────────────

async def _safe_news():
    try:
        return await news_agent.get_dashboard_news(["india", "world", "ai"])
    except Exception as exc:
        logger.error("[dashboard] news failed: %s", exc)
        return None

async def _safe_health(user_id: str):
    try:
        return await health_agent.get_dashboard_health(user_id)
    except Exception as exc:
        logger.error("[dashboard] health failed: %s", exc, exc_info=True)
        return None

async def _safe_memory(user_id: str):
    try:
        return await memory_agent.get_dashboard_memory(user_id)
    except Exception as exc:
        logger.error("[dashboard] memory failed: %s", exc, exc_info=True)
        return None

async def _safe_stocks():
    try:
        return await stock_agent.get_dashboard_stocks()
    except Exception as exc:
        logger.error("[dashboard] stocks failed: %s", exc, exc_info=True)
        return None

async def _safe_reminders(user_id: str):
    try:
        return await get_active_reminders(user_id)
    except Exception as exc:
        logger.error("[dashboard] reminders failed: %s", exc, exc_info=True)
        return []


@router.get("/dashboard")
async def dashboard(
    date_range: str = "this month",
    category: str | None = None,
    user_id: str = Depends(verify_token),
):
    normalized_range = date_range.strip().lower()
    normalized_category = str(category).strip().lower() if category else "all"
    cache_key = f"dashboard:{user_id}:{normalized_range}:{normalized_category}"

    cached_dashboard = await cache_get(cache_key)
    if cached_dashboard is not None:
        logger.debug("[dashboard] Returning cached dashboard for key %s", cache_key)
        return cached_dashboard

    filter_label, filter_start, filter_end = resolve_date_range(
        {"label": date_range},
        date_range,
    )
    _, today_start, today_end = resolve_date_range({"label": "today"}, "today")
    month_start, month_end = month_bounds(now_local())

    # ── Run ALL independent fetches concurrently ──
    (
        today_expense_total,
        month_expense_total,
        filtered_expense_total,
        month_income_total,
        recurring,
        cat_breakdown,
        budgets,
        recent,
        savings,
        f_trends,
        h_trends,
        news_data,
        health_data,
        memory_data,
        stock_data,
        reminders_data,
    ) = await asyncio.gather(
        expense_total(user_id, today_start, today_end),
        expense_total(user_id, month_start, month_end),
        expense_total(user_id, filter_start, filter_end, category),
        income_total(user_id, month_start, month_end),
        recurring_expenses(user_id),
        category_breakdown(user_id, filter_start, filter_end, category),
        budget_status(user_id, month_start, month_end),
        recent_expenses(user_id, filter_start, filter_end, category),
        savings_goals(user_id),
        finance_trends(user_id),
        health_agent.get_health_trends(user_id),
        _safe_news(),
        _safe_health(user_id),
        _safe_memory(user_id),
        _safe_stocks(),
        _safe_reminders(user_id),
    )

    data = {
        "finance": {
            "filters": {
                "dateRange": filter_label,
                "category": category,
            },
            "summary": {
                "todayExpenses": today_expense_total,
                "monthExpenses": month_expense_total,
                "filteredExpenses": filtered_expense_total,
                "monthIncome": month_income_total,
                "monthNet": month_income_total - month_expense_total,
                "recurringMonthly": recurring["total"],
            },
            "categoryBreakdown": cat_breakdown,
            "budgets": budgets,
            "recentExpenses": recent,
            "savingsGoals": savings,
            "recurringExpenses": recurring["items"],
            "trends": f_trends,
        },
        "news": news_data,
        "health": {
            **(health_data or {}),
            "trends": h_trends
        } if health_data else None,
        "memory": memory_data,
        "stocks": stock_data,
        "learning": None,
        "reminders": reminders_data,
    }

    await cache_set(cache_key, data, expire_seconds=DASHBOARD_CACHE_TTL)
    return data


# ─── SMS Expense Endpoints ────────────────────────────────────────────────────

@router.post("/expenses/sms")
async def ingest_sms_expense(
    payload: SmsExpenseRequest,
    user_id: str = Depends(verify_token),
):
    """
    Called by the Android app when a new payment SMS is received.
    Parses the SMS, auto-categorizes, and saves to MongoDB.
    """
    received_at = None
    if payload.received_at:
        try:
            received_at = datetime.fromisoformat(payload.received_at)
            if received_at.tzinfo is None:
                received_at = received_at.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    result = await sms_expense_agent.process_sms(
        user_id=user_id,
        sms_body=payload.sms_body,
        sender=payload.sender,
        received_at=received_at,
    )
    return result


@router.get("/expenses/sms")
async def get_sms_expenses(
    limit: int = 30,
    user_id: str = Depends(verify_token),
):
    """
    Returns the most recent SMS-auto-tracked expenses for the dashboard.
    """
    expenses = await sms_expense_agent.get_sms_expenses(user_id=user_id, limit=limit)
    return {"expenses": expenses, "count": len(expenses)}


@router.post("/expenses/deduplicate")
async def deduplicate_user_expenses(
    user_id: str = Depends(verify_token),
):
    """
    Finds and deletes all duplicate expense records for the current user.
    """
    result = await sms_expense_agent.deduplicate_expenses(user_id=user_id)
    return result



@router.get("/briefing")
async def get_daily_briefing(
    force_refresh: bool = False,
    user_id: str = Depends(verify_token),
):
    """
    Returns the comprehensive 'Today with Jarvis' proactive daily briefing.
    Strictly cached per user per calendar day — only invokes AI once per day.
    """
    today_str = now_local().strftime("%Y-%m-%d")
    cache_key = f"briefing:{user_id}:{today_str}"

    # 1. Check Redis fast cache (unless force-refreshing)
    if not force_refresh:
        cached_briefing = await cache_get(cache_key)
        if cached_briefing is not None:
            if isinstance(cached_briefing, dict) and not cached_briefing.get("date_key"):
                cached_briefing = {**cached_briefing, "date_key": today_str}
                await cache_set(cache_key, cached_briefing, expire_seconds=86400)
            return cached_briefing

        # 2. Check MongoDB persistent daily briefings collection
        try:
            db_doc = await get_collection("daily_briefings").find_one({
                "user_id": user_id,
                "date": today_str,
            })
            if db_doc and "data" in db_doc:
                # Re-populate Redis cache and return
                cached_data = db_doc["data"]
                if isinstance(cached_data, dict) and not cached_data.get("date_key"):
                    cached_data = {**cached_data, "date_key": today_str}
                await cache_set(cache_key, cached_data, expire_seconds=86400)
                return cached_data
        except Exception as db_err:
            logger.warning("[dashboard] MongoDB briefing cache lookup failed: %s", db_err)

    # 3. Cache miss or forced refresh: generate via AI
    try:
        user_doc = None
        if ObjectId.is_valid(user_id):
            user_doc = await get_collection("users").find_one({"_id": ObjectId(user_id)})
        user_name = user_doc.get("name", "User") if user_doc else "User"

        data = await briefing_agent.get_briefing_data(user_id=user_id, user_name=user_name)
        
        # 4. Save to Redis (24h)
        await cache_set(cache_key, data, expire_seconds=86400)

        # 5. Persist to MongoDB so cache survives server restarts
        try:
            await get_collection("daily_briefings").update_one(
                {"user_id": user_id, "date": today_str},
                {"$set": {"user_id": user_id, "date": today_str, "data": data, "updated_at": datetime.now(timezone.utc)}},
                upsert=True,
            )
        except Exception as db_save_err:
            logger.warning("[dashboard] MongoDB briefing cache save failed: %s", db_save_err)

        return data
    except Exception as exc:
        logger.error("[dashboard] get_daily_briefing failed: %s", exc, exc_info=True)
        # Do not make a second AI request after a failed generation (for example
        # after a Groq 429). The client can retry later and the normal Redis/Mongo
        # lookup will make a successful briefing fast on subsequent opens.
        raise HTTPException(status_code=503, detail="Daily briefing is temporarily unavailable.") from exc

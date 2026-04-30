import logging

from fastapi import APIRouter

from app.agents.health_agent import HealthAgent
from app.agents.news_agent import NewsAgent
from app.core.mongodb import get_collection
from app.tools.finance_tools import month_bounds, now_local, resolve_date_range

router = APIRouter()
news_agent = NewsAgent()
health_agent = HealthAgent()

logger = logging.getLogger(__name__)


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
    ).sort("created_at", -1).to_list(length=8)
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


@router.get("/dashboard")
async def dashboard(
    user_id: str = "default-user",
    date_range: str = "this month",
    category: str | None = None,
):
    filter_label, filter_start, filter_end = resolve_date_range(
        {"label": date_range},
        date_range,
    )
    _, today_start, today_end = resolve_date_range({"label": "today"}, "today")
    month_start, month_end = month_bounds(now_local())

    today_expense_total = await expense_total(user_id, today_start, today_end)
    month_expense_total = await expense_total(user_id, month_start, month_end)
    filtered_expense_total = await expense_total(user_id, filter_start, filter_end, category)
    month_income_total = await income_total(user_id, month_start, month_end)
    recurring = await recurring_expenses(user_id)

    try:
        news_data = await news_agent.get_dashboard_news(["india", "world", "ai"])
    except Exception:
        news_data = None

    try:
        health_data = await health_agent.get_dashboard_health(user_id)
    except Exception as exc:
        logger.error("[dashboard] get_dashboard_health failed: %s", exc, exc_info=True)
        health_data = None

    return {
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
            "categoryBreakdown": await category_breakdown(user_id, filter_start, filter_end, category),
            "budgets": await budget_status(user_id, month_start, month_end),
            "recentExpenses": await recent_expenses(user_id, filter_start, filter_end, category),
            "savingsGoals": await savings_goals(user_id),
            "recurringExpenses": recurring["items"],
        },
        "news": news_data,
        "health": health_data,
        "stocks": None,
        "learning": None,
        "reminders": [],
    }

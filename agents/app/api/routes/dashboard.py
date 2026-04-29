from fastapi import APIRouter

from app.core.mongodb import get_collection
from app.tools.finance_tools import month_bounds, now_local, resolve_date_range

router = APIRouter()


def serialize_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value) if value.__class__.__name__ == "ObjectId" else value


def serialize_document(document: dict):
    return {key: serialize_value(value) for key, value in document.items()}


async def expense_total(user_id: str, start, end, category: str | None = None):
    match = {
        "user_id": user_id,
        "$or": [
            {"occurred_at": {"$gte": start, "$lte": end}},
            {
                "occurred_at": {"$exists": False},
                "created_at": {"$gte": start, "$lte": end},
            },
        ],
    }

    if category:
        match["category"] = category

    pipeline = [
        {"$match": match},
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


async def category_breakdown(user_id: str, start, end):
    pipeline = [
        {
            "$match": {
                "user_id": user_id,
                "$or": [
                    {"occurred_at": {"$gte": start, "$lte": end}},
                    {
                        "occurred_at": {"$exists": False},
                        "created_at": {"$gte": start, "$lte": end},
                    },
                ],
            }
        },
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
        {"$sort": {"total": -1}},
    ]
    rows = await get_collection("expenses").aggregate(pipeline).to_list(length=20)
    return [
        {"category": row["_id"] or "Other", "total": row["total"]}
        for row in rows
    ]


async def recent_expenses(user_id: str):
    documents = await get_collection("expenses").find(
        {"user_id": user_id}
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
async def dashboard(user_id: str = "default-user"):
    _, today_start, today_end = resolve_date_range({"label": "today"}, "today")
    month_start, month_end = month_bounds(now_local())

    today_expense_total = await expense_total(user_id, today_start, today_end)
    month_expense_total = await expense_total(user_id, month_start, month_end)
    month_income_total = await income_total(user_id, month_start, month_end)
    recurring = await recurring_expenses(user_id)

    return {
        "finance": {
            "summary": {
                "todayExpenses": today_expense_total,
                "monthExpenses": month_expense_total,
                "monthIncome": month_income_total,
                "monthNet": month_income_total - month_expense_total,
                "recurringMonthly": recurring["total"],
            },
            "categoryBreakdown": await category_breakdown(user_id, month_start, month_end),
            "budgets": await budget_status(user_id, month_start, month_end),
            "recentExpenses": await recent_expenses(user_id),
            "savingsGoals": await savings_goals(user_id),
            "recurringExpenses": recurring["items"],
        },
        "news": None,
        "health": None,
        "stocks": None,
        "learning": None,
        "reminders": [],
    }

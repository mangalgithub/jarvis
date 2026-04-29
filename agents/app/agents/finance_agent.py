from datetime import UTC, datetime, time

from app.core.mongodb import get_collection
from app.tools.finance_tools import extract_expenses


class FinanceAgent:
    name = "finance"

    async def run(self, context: dict):
        message = context["message"]
        user_id = context["user_id"]
        expenses = extract_expenses(message)

        if not expenses:
            return {
                "reply": "I could not find an expense amount in that message. Try: I spent 250 on lunch.",
                "actions": [{"type": "expense_parse_empty"}],
            }

        collection = get_collection("expenses")
        now = datetime.now(UTC)

        documents = [
            {
                "user_id": user_id,
                "amount": expense["amount"],
                "description": expense["description"],
                "category": expense["category"],
                "source_text": message,
                "created_at": now,
            }
            for expense in expenses
        ]

        try:
            result = await collection.insert_many(documents)
            today_total = await self._get_total_for_period(
                user_id=user_id,
                start=datetime.combine(now.date(), time.min, tzinfo=UTC),
                end=now,
            )
            month_total = await self._get_total_for_period(
                user_id=user_id,
                start=datetime(now.year, now.month, 1, tzinfo=UTC),
                end=now,
            )
        except Exception as error:
            return {
                "reply": "I understood the expense, but MongoDB is not reachable. Start MongoDB and try again.",
                "actions": [
                    {
                        "type": "expense_storage_failed",
                        "error": str(error),
                        "expenses": expenses,
                    }
                ],
            }

        logged_total = sum(expense["amount"] for expense in expenses)
        expense_lines = ", ".join(
            f"₹{expense['amount']:g} {expense['category']} ({expense['description']})"
            for expense in expenses
        )

        return {
            "reply": (
                f"I logged ₹{logged_total:g} in expenses: {expense_lines}. "
                f"Today total: ₹{today_total:g}. Month total: ₹{month_total:g}."
            ),
            "actions": [
                {
                    "type": "expense_created",
                    "expense_ids": [str(expense_id) for expense_id in result.inserted_ids],
                    "expenses": expenses,
                    "today_total": today_total,
                    "month_total": month_total,
                }
            ],
        }

    async def _get_total_for_period(self, user_id: str, start: datetime, end: datetime):
        collection = get_collection("expenses")
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "created_at": {
                        "$gte": start,
                        "$lte": end,
                    },
                }
            },
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        result = await collection.aggregate(pipeline).to_list(length=1)

        if not result:
            return 0

        return result[0]["total"]

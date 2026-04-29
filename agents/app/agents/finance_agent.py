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
            return await self._handle_expense_query(user_id, message)

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
            f"Rs {expense['amount']:g} {expense['category']} ({expense['description']})"
            for expense in expenses
        )

        return {
            "reply": (
                f"I logged Rs {logged_total:g} in expenses: {expense_lines}. "
                f"Today total: Rs {today_total:g}. Month total: Rs {month_total:g}."
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

    async def _handle_expense_query(self, user_id: str, message: str):
        period_name, start, end = self._get_query_period(message)

        try:
            expenses = await self._get_expenses_for_period(user_id, start, end)
        except Exception as error:
            return {
                "reply": "I understood the expense query, but MongoDB is not reachable. Start MongoDB and try again.",
                "actions": [
                    {
                        "type": "expense_query_failed",
                        "error": str(error),
                        "period": period_name,
                    }
                ],
            }

        total = sum(expense["amount"] for expense in expenses)

        if not expenses:
            return {
                "reply": f"You have no expenses logged for {period_name}.",
                "actions": [
                    {
                        "type": "expense_query_result",
                        "period": period_name,
                        "expenses": [],
                        "total": 0,
                    }
                ],
            }

        expense_lines = "; ".join(
            f"Rs {expense['amount']:g} on {expense['description']} ({expense['category']})"
            for expense in expenses[:10]
        )
        extra_count = max(len(expenses) - 10, 0)
        extra_note = f" Plus {extra_count} more." if extra_count else ""

        return {
            "reply": (
                f"Your {period_name} expenses total Rs {total:g}: "
                f"{expense_lines}.{extra_note}"
            ),
            "actions": [
                {
                    "type": "expense_query_result",
                    "period": period_name,
                    "expenses": expenses,
                    "total": total,
                }
            ],
        }

    def _get_query_period(self, message: str):
        normalized_message = message.lower()
        now = datetime.now(UTC)

        if "today" in normalized_message:
            return "today", datetime.combine(now.date(), time.min, tzinfo=UTC), now

        if "month" in normalized_message or "monthly" in normalized_message:
            return "this month", datetime(now.year, now.month, 1, tzinfo=UTC), now

        if "all" in normalized_message or "total" in normalized_message:
            return "all time", None, now

        return "today", datetime.combine(now.date(), time.min, tzinfo=UTC), now

    async def _get_expenses_for_period(
        self,
        user_id: str,
        start: datetime | None,
        end: datetime,
    ):
        collection = get_collection("expenses")
        match = {"user_id": user_id, "created_at": {"$lte": end}}

        if start is not None:
            match["created_at"]["$gte"] = start

        cursor = collection.find(match).sort("created_at", -1)
        documents = await cursor.to_list(length=100)

        return [
            {
                "id": str(document["_id"]),
                "amount": document["amount"],
                "description": document["description"],
                "category": document["category"],
                "created_at": document["created_at"].isoformat(),
            }
            for document in documents
        ]

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

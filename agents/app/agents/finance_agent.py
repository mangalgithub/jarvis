from collections import defaultdict
from datetime import UTC, datetime, timedelta

from bson import ObjectId

from app.core.llm import LLMUnavailableError
from app.core.mongodb import get_collection
from app.tools.finance_tools import (
    categorize_expense,
    extract_expenses,
    month_bounds,
    normalize_payment_method,
    parse_date_to_utc,
    parse_finance_command,
    resolve_date_range,
)


class FinanceAgent:
    name = "finance"

    async def run(self, context: dict):
        message = context["message"]
        user_id = context["user_id"]

        try:
            command = await parse_finance_command(message)
        except LLMUnavailableError as error:
            fallback_expenses = extract_expenses(message)
            if not fallback_expenses:
                return {
                    "reply": "I could not understand the finance request because the LLM is unavailable.",
                    "actions": [
                        {
                            "type": "finance_parse_failed",
                            "source": "llm",
                            "error": str(error),
                        }
                    ],
                }
            command = {"operation": "log_expense", "expenses": fallback_expenses}

        operation = command["operation"]

        try:
            if operation == "log_expense":
                return await self._log_expenses(user_id, message, command)
            if operation == "query_expenses":
                return await self._query_expenses(user_id, message, command)
            if operation == "category_summary":
                return await self._category_summary(user_id, message, command)
            if operation == "update_expense":
                return await self._update_expense(user_id, command)
            if operation == "delete_expense":
                return await self._delete_expense(user_id, command)
            if operation == "set_budget":
                return await self._set_budget(user_id, command)
            if operation == "query_budget":
                return await self._query_budget(user_id)
            if operation == "log_income":
                return await self._log_income(user_id, message, command)
            if operation == "query_income":
                return await self._query_income(user_id, message, command)
            if operation == "set_recurring":
                return await self._set_recurring(user_id, command)
            if operation == "query_recurring":
                return await self._query_recurring(user_id)
            if operation == "set_savings_goal":
                return await self._set_savings_goal(user_id, command)
            if operation == "query_savings_goal":
                return await self._query_savings_goals(user_id)
            if operation == "analytics":
                return await self._analytics(user_id)
        except Exception as error:
            return {
                "reply": "I understood the finance request, but MongoDB is not reachable or the operation failed.",
                "actions": [
                    {
                        "type": "finance_operation_failed",
                        "operation": operation,
                        "error": str(error),
                    }
                ],
            }

        return await self._query_expenses(user_id, message, command)

    async def _log_expenses(self, user_id: str, message: str, command: dict):
        expenses = command.get("expenses") or extract_expenses(message)
        if not expenses:
            return {
                "reply": "I could not find an expense amount in that message. Try: I spent 250 on lunch.",
                "actions": [{"type": "expense_parse_empty"}],
            }

        now = datetime.now(UTC)
        documents = []
        duplicates = []

        for expense in expenses:
            amount = expense.get("amount")
            description = (expense.get("description") or "expense").strip()
            if amount is None:
                continue

            duplicate = await self._find_recent_duplicate(user_id, description, float(amount), now)
            if duplicate:
                duplicates.append(self._serialize_document(duplicate))
                continue

            documents.append(
                {
                    "user_id": user_id,
                    "amount": float(amount),
                    "description": description,
                    "category": categorize_expense(description, expense.get("category")),
                    "payment_method": normalize_payment_method(expense.get("payment_method")),
                    "source_text": message,
                    "occurred_at": parse_date_to_utc(expense.get("date")),
                    "created_at": now,
                    "updated_at": now,
                }
            )

        if not documents:
            if not duplicates:
                return {
                    "reply": "I understood the expense request, but no valid amount was found.",
                    "actions": [{"type": "expense_parse_empty"}],
                }

            return {
                "reply": "I found a similar expense logged recently, so I did not add it again.",
                "actions": [
                    {
                        "type": "expense_duplicate_detected",
                        "duplicates": duplicates,
                    }
                ],
            }

        result = await get_collection("expenses").insert_many(documents)
        today_label, today_start, today_end = resolve_date_range(
            {"label": "today"},
            "today",
        )
        month_start, _ = month_bounds(datetime.now().astimezone())
        today_total = await self._expense_total(user_id, today_start, today_end)
        month_total = await self._expense_total(user_id, month_start, datetime.now(UTC))
        logged_total = sum(document["amount"] for document in documents)
        expense_lines = ", ".join(
            f"{self._money(document['amount'])} {document['category']} ({document['description']})"
            for document in documents
        )

        return {
            "reply": (
                f"I logged {self._money(logged_total)} in expenses: {expense_lines}. "
                f"{today_label.title()} total: {self._money(today_total)}. "
                f"Month total: {self._money(month_total)}."
            ),
            "actions": [
                {
                    "type": "expense_created",
                    "expense_ids": [str(expense_id) for expense_id in result.inserted_ids],
                    "expenses": self._serialize_documents(documents),
                    "today_total": today_total,
                    "month_total": month_total,
                    "duplicates": duplicates,
                }
            ],
        }

    async def _query_expenses(self, user_id: str, message: str, command: dict):
        period_name, start, end = resolve_date_range(command.get("date_range"), message)
        expenses = await self._get_expenses(user_id, start, end, command.get("filters", {}))
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
            f"{self._money(expense['amount'])} on {expense['description']} ({expense['category']})"
            for expense in expenses[:10]
        )
        extra_count = max(len(expenses) - 10, 0)
        extra_note = f" Plus {extra_count} more." if extra_count else ""

        return {
            "reply": f"Your {period_name} expenses total {self._money(total)}: {expense_lines}.{extra_note}",
            "actions": [
                {
                    "type": "expense_query_result",
                    "period": period_name,
                    "expenses": expenses,
                    "total": total,
                }
            ],
        }

    async def _category_summary(self, user_id: str, message: str, command: dict):
        period_name, start, end = resolve_date_range(command.get("date_range"), message)
        expenses = await self._get_expenses(user_id, start, end, command.get("filters", {}))
        totals = defaultdict(float)

        for expense in expenses:
            totals[expense["category"]] += expense["amount"]

        summary = [
            {"category": category, "total": total}
            for category, total in sorted(totals.items(), key=lambda item: item[1], reverse=True)
        ]

        if not summary:
            return {
                "reply": f"No category spending found for {period_name}.",
                "actions": [{"type": "category_summary", "period": period_name, "summary": []}],
            }

        lines = ", ".join(f"{item['category']}: {self._money(item['total'])}" for item in summary)
        return {
            "reply": f"Category-wise spending for {period_name}: {lines}.",
            "actions": [{"type": "category_summary", "period": period_name, "summary": summary}],
        }

    async def _update_expense(self, user_id: str, command: dict):
        update = command.get("update") or {}
        document = await self._find_matching_expense(
            user_id,
            update.get("match_description") or update.get("description"),
            update.get("amount"),
        )

        if not document:
            return {
                "reply": "I could not find a matching expense to update.",
                "actions": [{"type": "expense_update_not_found", "update": update}],
            }

        set_fields = {"updated_at": datetime.now(UTC)}
        if update.get("amount") is not None:
            set_fields["amount"] = float(update["amount"])
        if update.get("description"):
            set_fields["description"] = update["description"]
        if update.get("category"):
            set_fields["category"] = categorize_expense(
                set_fields.get("description", document.get("description", "expense")),
                update.get("category"),
            )
        if update.get("payment_method"):
            set_fields["payment_method"] = normalize_payment_method(update.get("payment_method"))

        await get_collection("expenses").update_one({"_id": document["_id"]}, {"$set": set_fields})
        return {
            "reply": "I updated the matching expense.",
            "actions": [
                {
                    "type": "expense_updated",
                    "expense_id": str(document["_id"]),
                    "updated_fields": self._serialize_value(set_fields),
                }
            ],
        }

    async def _delete_expense(self, user_id: str, command: dict):
        delete = command.get("delete") or {}
        document = await self._find_matching_expense(
            user_id,
            delete.get("match_description") or delete.get("description"),
            delete.get("amount"),
        )

        if not document:
            return {
                "reply": "I could not find a matching expense to delete.",
                "actions": [{"type": "expense_delete_not_found", "delete": delete}],
            }

        await get_collection("expenses").delete_one({"_id": document["_id"]})
        return {
            "reply": f"I deleted {self._money(document['amount'])} on {document.get('description', 'expense')}.",
            "actions": [
                {
                    "type": "expense_deleted",
                    "expense": self._serialize_document(document),
                }
            ],
        }

    async def _set_budget(self, user_id: str, command: dict):
        budget = command.get("budget") or {}
        category = categorize_expense(budget.get("category") or "Other", budget.get("category"))
        amount = budget.get("amount")

        if amount is None:
            return {
                "reply": "Tell me the budget amount, for example: set Food budget 5000 per month.",
                "actions": [{"type": "budget_parse_empty"}],
            }

        document = {
            "user_id": user_id,
            "category": category,
            "amount": float(amount),
            "period": budget.get("period") or "monthly",
            "updated_at": datetime.now(UTC),
        }
        await get_collection("budgets").update_one(
            {"user_id": user_id, "category": category, "period": document["period"]},
            {"$set": document, "$setOnInsert": {"created_at": datetime.now(UTC)}},
            upsert=True,
        )

        return {
            "reply": f"I set your {category} budget to {self._money(document['amount'])} {document['period']}.",
            "actions": [{"type": "budget_set", "budget": document}],
        }

    async def _query_budget(self, user_id: str):
        budgets = await get_collection("budgets").find({"user_id": user_id}).to_list(length=100)
        if not budgets:
            return {
                "reply": "You do not have any budgets set yet.",
                "actions": [{"type": "budget_query_result", "budgets": []}],
            }

        month_start, _ = month_bounds(datetime.now().astimezone())
        now = datetime.now(UTC)
        enriched = []

        for budget in budgets:
            spent = await self._expense_total(
                user_id,
                month_start,
                now,
                {"category": budget["category"]},
            )
            enriched.append(
                {
                    "category": budget["category"],
                    "budget": budget["amount"],
                    "spent": spent,
                    "remaining": budget["amount"] - spent,
                    "period": budget.get("period", "monthly"),
                }
            )

        lines = ", ".join(
            f"{item['category']}: {self._money(item['spent'])}/{self._money(item['budget'])}"
            for item in enriched
        )
        return {
            "reply": f"Budget status: {lines}.",
            "actions": [{"type": "budget_query_result", "budgets": enriched}],
        }

    async def _log_income(self, user_id: str, message: str, command: dict):
        income_items = command.get("income") or []
        documents = []
        now = datetime.now(UTC)

        for item in income_items:
            if item.get("amount") is None:
                continue
            documents.append(
                {
                    "user_id": user_id,
                    "amount": float(item["amount"]),
                    "description": item.get("description") or "income",
                    "source": item.get("source") or item.get("description") or "income",
                    "source_text": message,
                    "occurred_at": parse_date_to_utc(item.get("date")),
                    "created_at": now,
                }
            )

        if not documents:
            return {
                "reply": "I could not find an income amount in that message.",
                "actions": [{"type": "income_parse_empty"}],
            }

        result = await get_collection("income").insert_many(documents)
        total = sum(document["amount"] for document in documents)
        return {
            "reply": f"I logged {self._money(total)} as income.",
            "actions": [
                {
                    "type": "income_created",
                    "income_ids": [str(income_id) for income_id in result.inserted_ids],
                    "income": self._serialize_documents(documents),
                }
            ],
        }

    async def _query_income(self, user_id: str, message: str, command: dict):
        period_name, start, end = resolve_date_range(command.get("date_range"), message)
        income_items = await self._get_income(user_id, start, end)
        total = sum(item["amount"] for item in income_items)
        return {
            "reply": f"Your {period_name} income total is {self._money(total)}.",
            "actions": [
                {
                    "type": "income_query_result",
                    "period": period_name,
                    "income": income_items,
                    "total": total,
                }
            ],
        }

    async def _set_recurring(self, user_id: str, command: dict):
        recurring = command.get("recurring") or {}
        if recurring.get("amount") is None:
            return {
                "reply": "Tell me the recurring amount, for example: Netflix 649 every month.",
                "actions": [{"type": "recurring_parse_empty"}],
            }

        description = recurring.get("description") or "recurring expense"
        document = {
            "user_id": user_id,
            "description": description,
            "amount": float(recurring["amount"]),
            "category": categorize_expense(description, recurring.get("category")),
            "frequency": recurring.get("frequency") or "monthly",
            "payment_method": normalize_payment_method(recurring.get("payment_method")),
            "created_at": datetime.now(UTC),
        }
        result = await get_collection("recurring_expenses").insert_one(document)
        return {
            "reply": f"I added recurring {description} for {self._money(document['amount'])} {document['frequency']}.",
            "actions": [
                {
                    "type": "recurring_expense_created",
                    "recurring_id": str(result.inserted_id),
                    "recurring": self._serialize_document(document),
                }
            ],
        }

    async def _query_recurring(self, user_id: str):
        recurring = await get_collection("recurring_expenses").find({"user_id": user_id}).to_list(length=100)
        serialized = self._serialize_documents(recurring)

        if not serialized:
            return {
                "reply": "You do not have any recurring expenses set.",
                "actions": [{"type": "recurring_expense_query_result", "recurring": []}],
            }

        total = sum(item["amount"] for item in serialized)
        lines = ", ".join(
            f"{item['description']} {self._money(item['amount'])} {item.get('frequency', 'monthly')}"
            for item in serialized[:10]
        )
        return {
            "reply": f"Your recurring expenses total {self._money(total)}: {lines}.",
            "actions": [{"type": "recurring_expense_query_result", "recurring": serialized, "total": total}],
        }

    async def _set_savings_goal(self, user_id: str, command: dict):
        goal = command.get("savings_goal") or {}
        target = goal.get("target_amount")
        name = goal.get("name") or "savings goal"

        if target is None:
            return {
                "reply": "Tell me the target amount, for example: save 100000 for laptop.",
                "actions": [{"type": "savings_goal_parse_empty"}],
            }

        document = {
            "user_id": user_id,
            "name": name,
            "target_amount": float(target),
            "saved_amount": float(goal.get("saved_amount") or 0),
            "target_date": goal.get("target_date"),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        result = await get_collection("savings_goals").insert_one(document)
        return {
            "reply": f"I created your {name} savings goal for {self._money(document['target_amount'])}.",
            "actions": [
                {
                    "type": "savings_goal_created",
                    "goal_id": str(result.inserted_id),
                    "goal": self._serialize_document(document),
                }
            ],
        }

    async def _query_savings_goals(self, user_id: str):
        goals = await get_collection("savings_goals").find({"user_id": user_id}).to_list(length=100)
        serialized = self._serialize_documents(goals)

        if not serialized:
            return {
                "reply": "You do not have any savings goals yet.",
                "actions": [{"type": "savings_goal_query_result", "goals": []}],
            }

        lines = ", ".join(
            self._format_goal_progress(goal)
            for goal in serialized
        )
        return {
            "reply": f"Your savings goals: {lines}.",
            "actions": [{"type": "savings_goal_query_result", "goals": serialized}],
        }

    async def _analytics(self, user_id: str):
        now = datetime.now(UTC)
        current_month_start, _ = month_bounds(datetime.now().astimezone())
        previous_month_end = current_month_start - timedelta(microseconds=1)
        previous_month_start, _ = month_bounds(previous_month_end.astimezone())
        current_expenses = await self._get_expenses(user_id, current_month_start, now, {})
        previous_expenses = await self._get_expenses(user_id, previous_month_start, previous_month_end, {})
        current_total = sum(expense["amount"] for expense in current_expenses)
        previous_total = sum(expense["amount"] for expense in previous_expenses)
        category_totals = defaultdict(float)

        for expense in current_expenses:
            category_totals[expense["category"]] += expense["amount"]

        top_category = max(category_totals.items(), key=lambda item: item[1], default=("None", 0))
        biggest = max(current_expenses, key=lambda expense: expense["amount"], default=None)
        delta = current_total - previous_total
        biggest_text = (
            f" Biggest expense: {self._money(biggest['amount'])} on {biggest['description']}."
            if biggest
            else ""
        )

        return {
            "reply": (
                f"This month you spent {self._money(current_total)}, "
                f"{self._money(abs(delta))} {'more' if delta >= 0 else 'less'} than last month. "
                f"Top category: {top_category[0]} ({self._money(top_category[1])})."
                f"{biggest_text}"
            ),
            "actions": [
                {
                    "type": "finance_analytics",
                    "current_month_total": current_total,
                    "previous_month_total": previous_total,
                    "top_category": {"category": top_category[0], "total": top_category[1]},
                    "biggest_expense": biggest,
                }
            ],
        }

    async def _find_matching_expense(self, user_id: str, description: str | None, amount):
        query = {"user_id": user_id}
        if description:
            query["description"] = {"$regex": re_escape(description), "$options": "i"}
        if amount is not None:
            query["amount"] = float(amount)
        return await get_collection("expenses").find_one(query, sort=[("created_at", -1)])

    async def _find_recent_duplicate(
        self,
        user_id: str,
        description: str,
        amount: float,
        now: datetime,
    ):
        return await get_collection("expenses").find_one(
            {
                "user_id": user_id,
                "amount": amount,
                "description": {"$regex": re_escape(description), "$options": "i"},
                "created_at": {"$gte": now - timedelta(minutes=5)},
            },
            sort=[("created_at", -1)],
        )

    async def _get_expenses(self, user_id: str, start: datetime | None, end: datetime, filters: dict):
        query = self._date_query(user_id, start, end)
        category = filters.get("category")
        payment_method = filters.get("payment_method")
        description = filters.get("description")

        if category:
            query["category"] = categorize_expense(category, category)
        if payment_method:
            query["payment_method"] = normalize_payment_method(payment_method)
        if description:
            query["description"] = {"$regex": re_escape(description), "$options": "i"}

        documents = await get_collection("expenses").find(query).sort("created_at", -1).to_list(length=100)
        return self._serialize_documents(documents)

    async def _get_income(self, user_id: str, start: datetime | None, end: datetime):
        documents = await get_collection("income").find(
            self._date_query(user_id, start, end)
        ).sort("created_at", -1).to_list(length=100)
        return self._serialize_documents(documents)

    async def _expense_total(
        self,
        user_id: str,
        start: datetime | None,
        end: datetime,
        filters: dict | None = None,
    ):
        expenses = await self._get_expenses(user_id, start, end, filters or {})
        return sum(expense["amount"] for expense in expenses)

    def _date_query(self, user_id: str, start: datetime | None, end: datetime):
        if start is None:
            return {"user_id": user_id}

        return {
            "user_id": user_id,
            "$or": [
                {"occurred_at": {"$gte": start, "$lte": end}},
                {
                    "occurred_at": {"$exists": False},
                    "created_at": {"$gte": start, "$lte": end},
                },
            ],
        }

    def _serialize_documents(self, documents: list[dict]):
        return [self._serialize_document(document) for document in documents]

    def _serialize_document(self, document: dict):
        return {
            key: self._serialize_value(value)
            for key, value in document.items()
        }

    def _serialize_value(self, value):
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {key: self._serialize_value(item) for key, item in value.items()}
        return value

    def _money(self, amount: float):
        return f"Rs {amount:g}"

    def _format_goal_progress(self, goal: dict):
        saved = goal.get("saved_amount", 0)
        target = goal["target_amount"]
        base = f"{goal['name']}: {self._money(saved)}/{self._money(target)}"
        target_date = goal.get("target_date")

        if not target_date:
            return base

        try:
            deadline = datetime.fromisoformat(target_date).date()
        except ValueError:
            return base

        today = datetime.now(UTC).date()
        days_left = max((deadline - today).days, 1)
        months_left = max(days_left / 30, 1)
        monthly_required = max((target - saved) / months_left, 0)
        return f"{base}, about {self._money(monthly_required)} per month needed"


def re_escape(value: str):
    import re

    return re.escape(value)

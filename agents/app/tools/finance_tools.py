import json
import re
from datetime import UTC, datetime, time, timedelta, timezone

from app.core.llm import generate_response

LOCAL_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

EXPENSE_CATEGORIES = {
    "Food",
    "Grocery",
    "Travel",
    "Shopping",
    "Investment",
    "Bills",
    "Health",
    "Entertainment",
    "Education",
    "Rent",
    "Other",
}

CATEGORY_KEYWORDS = {
    "Food": [
        "breakfast",
        "lunch",
        "dinner",
        "tea",
        "coffee",
        "snack",
        "restaurant",
        "food",
        "meal",
        "swiggy",
        "zomato",
        "dominos",
        "pizza",
    ],
    "Grocery": [
        "grocery",
        "groceries",
        "grocies",
        "vegetable",
        "milk",
        "fruit",
        "rice",
        "dal",
        "blinkit",
        "zepto",
        "bigbasket",
    ],
    "Travel": ["bus", "train", "cab", "uber", "ola", "metro", "petrol", "fuel", "rapido"],
    "Shopping": ["shirt", "clothes", "shoes", "amazon", "flipkart", "myntra", "shopping"],
    "Investment": ["sip", "mutual fund", "stock", "investment", "invested"],
    "Bills": ["bill", "electricity", "wifi", "internet", "rent", "recharge", "emi"],
    "Health": ["medicine", "doctor", "gym", "protein", "health", "whey"],
    "Entertainment": ["movie", "netflix", "spotify", "prime", "hotstar", "game"],
    "Education": ["course", "book", "college", "tuition", "udemy", "learning"],
    "Rent": ["rent"],
}

PAYMENT_METHODS = {"cash", "upi", "card", "bank", "wallet", "unknown"}

FINANCE_OPERATIONS = {
    "log_expense",
    "query_expenses",
    "category_summary",
    "update_expense",
    "delete_expense",
    "set_budget",
    "query_budget",
    "log_income",
    "query_income",
    "set_recurring",
    "query_recurring",
    "set_savings_goal",
    "query_savings_goal",
    "analytics",
}


def now_local() -> datetime:
    return datetime.now(LOCAL_TIMEZONE)


def local_day_bounds(day: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(day.date(), time.min, tzinfo=LOCAL_TIMEZONE)
    end = datetime.combine(day.date(), time.max, tzinfo=LOCAL_TIMEZONE)
    return start.astimezone(UTC), end.astimezone(UTC)


def month_bounds(day: datetime) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, 1, tzinfo=LOCAL_TIMEZONE)
    if day.month == 12:
        next_month = datetime(day.year + 1, 1, 1, tzinfo=LOCAL_TIMEZONE)
    else:
        next_month = datetime(day.year, day.month + 1, 1, tzinfo=LOCAL_TIMEZONE)
    return start.astimezone(UTC), (next_month - timedelta(microseconds=1)).astimezone(UTC)


def parse_date_to_utc(date_text: str | None, fallback: datetime | None = None) -> datetime:
    if not date_text:
        local_date = fallback or now_local()
    else:
        local_date = datetime.fromisoformat(date_text).replace(tzinfo=LOCAL_TIMEZONE)

    local_noon = datetime.combine(local_date.date(), time(hour=12), tzinfo=LOCAL_TIMEZONE)
    return local_noon.astimezone(UTC)


def resolve_date_range(date_range: dict | None, message: str) -> tuple[str, datetime | None, datetime]:
    normalized_message = message.lower()
    current = now_local()
    label = (date_range or {}).get("label") or ""
    start_text = (date_range or {}).get("start_date")
    end_text = (date_range or {}).get("end_date")

    if start_text and end_text:
        start = datetime.fromisoformat(start_text).replace(tzinfo=LOCAL_TIMEZONE)
        end = datetime.fromisoformat(end_text).replace(tzinfo=LOCAL_TIMEZONE)
        return (
            label or f"{start_text} to {end_text}",
            datetime.combine(start.date(), time.min, tzinfo=LOCAL_TIMEZONE).astimezone(UTC),
            datetime.combine(end.date(), time.max, tzinfo=LOCAL_TIMEZONE).astimezone(UTC),
        )

    if "yesterday" in normalized_message or label == "yesterday":
        start, end = local_day_bounds(current - timedelta(days=1))
        return "yesterday", start, end

    if "week" in normalized_message or label in {"this week", "week"}:
        start_local = datetime.combine(
            (current - timedelta(days=current.weekday())).date(),
            time.min,
            tzinfo=LOCAL_TIMEZONE,
        )
        return "this week", start_local.astimezone(UTC), current.astimezone(UTC)

    if "month" in normalized_message or label in {"this month", "month"}:
        start, _ = month_bounds(current)
        return "this month", start, current.astimezone(UTC)

    if "today" in normalized_message or label == "today":
        start, end = local_day_bounds(current)
        return "today", start, end

    if "all time" in normalized_message or label == "all time":
        return "all time", None, current.astimezone(UTC)

    return "today", *local_day_bounds(current)


def categorize_expense(description: str, category: str | None = None) -> str:
    if category in EXPENSE_CATEGORIES:
        return category

    normalized_description = description.lower()
    for category_name, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in normalized_description for keyword in keywords):
            return category_name

    return "Other"


def normalize_payment_method(payment_method: str | None) -> str:
    if not payment_method:
        return "unknown"

    normalized = payment_method.lower().strip()
    return normalized if normalized in PAYMENT_METHODS else "unknown"


def extract_expenses(text: str) -> list[dict]:
    normalized_text = (
        text.replace("₹", " rupees ")
        .replace("â‚¹", " rupees ")
        .replace("Ã¢â€šÂ¹", " rupees ")
    )
    pattern = re.compile(
        r"(?P<amount>\d+(?:\.\d+)?)\s*(?:rs|rupees|inr)?\s*(?:on|for|in)?\s*(?P<description>[a-zA-Z][a-zA-Z\s]{0,40})?",
        re.IGNORECASE,
    )
    expenses = []

    for match in pattern.finditer(normalized_text):
        raw_description = (match.group("description") or "expense").strip()
        description = re.split(
            r"\b(?:and|then|also|plus|,|\.|today|yesterday)\b",
            raw_description,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip() or "expense"
        expenses.append(
            {
                "amount": float(match.group("amount")),
                "description": description,
                "category": categorize_expense(description),
                "date": None,
                "payment_method": "unknown",
            }
        )

    return expenses


def parse_json_object(response_text: str) -> dict:
    match = re.search(r"\{.*\}", response_text, flags=re.DOTALL)
    if not match:
        return {}

    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}

    return payload if isinstance(payload, dict) else {}


def normalize_finance_command(payload: dict, message: str) -> dict:
    operation = payload.get("operation")
    if operation not in FINANCE_OPERATIONS:
        operation = "query_expenses"

    command = {
        "operation": operation,
        "date_range": payload.get("date_range") if isinstance(payload.get("date_range"), dict) else {},
        "expenses": payload.get("expenses") if isinstance(payload.get("expenses"), list) else [],
        "income": payload.get("income") if isinstance(payload.get("income"), list) else [],
        "budget": payload.get("budget") if isinstance(payload.get("budget"), dict) else {},
        "recurring": payload.get("recurring") if isinstance(payload.get("recurring"), dict) else {},
        "savings_goal": payload.get("savings_goal") if isinstance(payload.get("savings_goal"), dict) else {},
        "filters": payload.get("filters") if isinstance(payload.get("filters"), dict) else {},
        "update": payload.get("update") if isinstance(payload.get("update"), dict) else {},
        "delete": payload.get("delete") if isinstance(payload.get("delete"), dict) else {},
    }

    if operation == "log_expense" and not command["expenses"]:
        command["expenses"] = extract_expenses(message)

    return command


def parse_direct_expense_action(message: str) -> dict | None:
    delete_match = re.search(
        r"\bdelete\s+expense\s+id\s+(?P<expense_id>[a-fA-F0-9]{24})\b",
        message,
    )
    if delete_match:
        return normalize_finance_command(
            {
                "operation": "delete_expense",
                "delete": {"expense_id": delete_match.group("expense_id")},
            },
            message,
        )

    update_match = re.search(
        r"\bupdate\s+expense\s+id\s+(?P<expense_id>[a-fA-F0-9]{24})\s+amount\s+to\s+(?P<amount>\d+(?:\.\d+)?)\b",
        message,
    )
    if update_match:
        return normalize_finance_command(
            {
                "operation": "update_expense",
                "update": {
                    "expense_id": update_match.group("expense_id"),
                    "amount": float(update_match.group("amount")),
                },
            },
            message,
        )

    return None


async def parse_finance_command(message: str, user_memory: str = "") -> dict:
    direct_command = parse_direct_expense_action(message)
    if direct_command:
        return direct_command

    current_date = now_local().date().isoformat()
    categories = ", ".join(sorted(EXPENSE_CATEGORIES))
    operations = ", ".join(sorted(FINANCE_OPERATIONS))
    prompt = f"""You are Jarvis's financial parser. Parse the user's message into strict JSON.
Today is {current_date} (Asia/Kolkata).
User memory (context): {user_memory if user_memory else "None"}

Allowed operations: {", ".join(sorted(FINANCE_OPERATIONS))}
Allowed expense categories: {categories}
Allowed payment methods: cash, upi, card, bank, wallet, unknown

Use this JSON shape:
{{
  "operation": "log_expense",
  "date_range": {{"label": "today", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}},
  "expenses": [{{"amount": 250, "description": "lunch", "category": "Food", "date": "YYYY-MM-DD", "payment_method": "upi"}}],
  "income": [{{"amount": 50000, "description": "salary", "date": "YYYY-MM-DD", "source": "salary"}}],
  "budget": {{"category": "Food", "amount": 5000, "period": "monthly"}},
  "recurring": {{"description": "Netflix", "amount": 649, "category": "Entertainment", "frequency": "monthly", "payment_method": "card"}},
  "savings_goal": {{"name": "laptop", "target_amount": 100000, "target_date": "YYYY-MM-DD"}},
  "filters": {{"category": "Food", "payment_method": "upi", "description": "lunch"}},
  "update": {{"expense_id": "mongo_id", "match_description": "lunch", "amount": 300, "category": "Food", "description": "lunch"}},
  "delete": {{"expense_id": "mongo_id", "match_description": "tea", "amount": 100}}
}}

Rules:
- Return only JSON.
- Use null for unknown optional values.
- For expense questions, use query_expenses.
- For category-wise spending, use category_summary.
- For budget questions, use query_budget.
- For salary/income credits, use log_income.
- For recurring bills/subscriptions, use set_recurring.
- For savings targets, use set_savings_goal.

User message: {message}
"""

    response_text = await generate_response(
        prompt,
        system_prompt="You parse finance commands for Jarvis. Return strict JSON only.",
        temperature=0,
    )
    return normalize_finance_command(parse_json_object(response_text), message)

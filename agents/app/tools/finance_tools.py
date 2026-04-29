import re

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
    ],
    "Grocery": ["grocery", "groceries", "vegetable", "milk", "fruit", "rice", "dal"],
    "Travel": ["bus", "train", "cab", "uber", "ola", "metro", "petrol", "fuel"],
    "Shopping": ["shirt", "clothes", "shoes", "amazon", "flipkart", "shopping"],
    "Investment": ["sip", "mutual fund", "stock", "investment", "invested"],
    "Bills": ["bill", "electricity", "wifi", "internet", "rent", "recharge"],
    "Health": ["medicine", "doctor", "gym", "protein", "health"],
}


def categorize_expense(description: str) -> str:
    normalized_description = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in normalized_description for keyword in keywords):
            return category

    return "Other"


def extract_expenses(text: str) -> list[dict]:
    normalized_text = text.replace("₹", " rupees ")
    pattern = re.compile(
        r"(?P<amount>\d+(?:\.\d+)?)\s*(?:rs|rupees|inr)?\s*(?:on|for|in)?\s*(?P<description>[a-zA-Z][a-zA-Z\s]{0,40})?",
        re.IGNORECASE,
    )

    expenses = []

    for match in pattern.finditer(normalized_text):
        amount = float(match.group("amount"))
        raw_description = (match.group("description") or "expense").strip()
        description = re.split(
            r"\b(?:and|then|also|plus|,|\.|today|yesterday)\b",
            raw_description,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        if not description:
            description = "expense"

        expenses.append(
            {
                "amount": amount,
                "description": description,
                "category": categorize_expense(description),
            }
        )

    return expenses

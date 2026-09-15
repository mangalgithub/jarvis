"""
SMS Expense Agent

Receives parsed SMS data, uses Groq to auto-categorize the expense,
and saves it to MongoDB with source="sms" so the dashboard can distinguish
SMS-tracked vs manually-logged expenses.
"""

import json
import logging
import re
from datetime import datetime, timezone

from app.core.llm import LLMUnavailableError, generate_response
from pymongo.errors import DuplicateKeyError
from app.core.mongodb import get_collection
from app.core.sms_parser import parse_payment_sms

logger = logging.getLogger(__name__)

# ─── Categories available for auto-classification ─────────────────────────────
EXPENSE_CATEGORIES = [
    "Food & Dining",
    "Transport",
    "Shopping",
    "Entertainment",
    "Bills & Utilities",
    "Health & Medical",
    "Groceries",
    "Travel",
    "Education",
    "Fuel",
    "Clothing",
    "Electronics",
    "Subscriptions",
    "Personal Care",
    "Transfers",
    "Other",
]

_CATEGORIZE_SYSTEM_PROMPT = (
    "You are a financial categorization assistant. "
    "Given a merchant name or payment description, return ONLY the most appropriate "
    "category from this list (exact match required):\n"
    + "\n".join(f"- {c}" for c in EXPENSE_CATEGORIES)
    + "\n\nRespond with ONLY the category name, nothing else."
)

# ─── Simple keyword-based fallback categorizer ────────────────────────────────
_KEYWORD_MAP = {
    "Food & Dining": [
        "zomato", "swiggy", "restaurant", "cafe", "hotel", "food", "pizza",
        "burger", "eat", "dining", "biryani", "mcdonalds", "kfc", "dominos",
        "subway", "starbucks", "chai", "tea", "coffee",
    ],
    "Transport": [
        "uber", "ola", "rapido", "auto", "taxi", "cab", "bus", "metro",
        "train", "irctc", "redbus", "makemytrip transport",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "nykaa", "meesho", "snapdeal",
        "shopsy", "tata cliq", "reliance", "walmart",
    ],
    "Groceries": [
        "bigbasket", "blinkit", "grofers", "zepto", "jiomart", "dmart",
        "grocery", "vegetables", "fruits", "milk", "supermarket",
    ],
    "Entertainment": [
        "bookmyshow", "paytm movies", "pvr", "inox", "cinepolis", "netflix",
        "hotstar", "prime video", "spotify", "youtube",
    ],
    "Bills & Utilities": [
        "electricity", "bescom", "msedcl", "bses", "tata power", "adani",
        "gas", "water", "broadband", "airtel", "jio", "vi ", "vodafone",
        "bsnl", "recharge", "mobile bill",
    ],
    "Fuel": [
        "petrol", "diesel", "hp ", "indian oil", "bharat petroleum", "fuel",
        "iocl", "hpcl", "bpcl",
    ],
    "Health & Medical": [
        "apollo", "medplus", "netmeds", "1mg", "pharmeasy", "pharmacy",
        "hospital", "clinic", "doctor", "medical", "medicine",
    ],
    "Subscriptions": [
        "netflix", "amazon prime", "hotstar", "spotify", "adobe", "microsoft",
        "google", "apple", "subscription",
    ],
    "Travel": [
        "makemytrip", "goibibo", "cleartrip", "yatra", "oyo", "airbnb",
        "hotel", "flight", "airline", "indigo", "spicejet", "airindia",
    ],
    "Education": [
        "udemy", "coursera", "byju", "unacademy", "vedantu", "toppr",
        "school", "college", "university", "tuition", "books",
    ],
    "Transfers": [
        "transfer", "sent to", "paid to", "wallet", "bank",
    ],
}


def _keyword_categorize(merchant: str, description: str) -> str:
    combined = (merchant or "" + " " + description).lower()
    for category, keywords in _KEYWORD_MAP.items():
        if any(kw in combined for kw in keywords):
            return category
    return "Other"


async def _ai_categorize(merchant: str, payment_method: str) -> str:
    """Use Groq to categorize if merchant is known."""
    if not merchant:
        return "Other"
    prompt = f"Merchant: {merchant}\nPayment Method: {payment_method}"
    try:
        result = await generate_response(
            prompt,
            system_prompt=_CATEGORIZE_SYSTEM_PROMPT,
            temperature=0,
        )
        result = result.strip()
        if result in EXPENSE_CATEGORIES:
            return result
        # fallback to keyword
        return _keyword_categorize(merchant, "")
    except LLMUnavailableError:
        return _keyword_categorize(merchant, "")


class SmsExpenseAgent:
    """Processes incoming SMS payloads and logs them as expenses."""

    async def process_sms(
        self,
        user_id: str,
        sms_body: str,
        sender: str = "",
        received_at: datetime | None = None,
    ) -> dict:
        """
        Parse a raw SMS, categorize the expense, and save to MongoDB.

        Returns a dict with:
            success: bool
            expense: dict | None
            message: str
        """
        # 1. Parse
        parsed = parse_payment_sms(sms_body, sender, received_at)
        if parsed is None:
            return {
                "success": False,
                "expense": None,
                "message": "SMS does not appear to be a payment message.",
            }

        # Only track debits (outgoing payments)
        if parsed["transaction_type"] == "credit":
            return {
                "success": False,
                "expense": None,
                "message": "SMS is a credit/incoming transaction — skipping.",
            }

        # 2. Categorize
        merchant = parsed.get("merchant") or ""
        payment_method = parsed.get("payment_method", "")
        # Try keyword first (faster), fall back to AI
        category = _keyword_categorize(merchant, "")
        if category == "Other" and merchant:
            category = await _ai_categorize(merchant, payment_method)

        # 3. Build expense document
        now = datetime.now(timezone.utc)
        description = merchant or f"Payment via {payment_method}"

        document = {
            "user_id": user_id,
            "amount": parsed["amount"],
            "description": description,
            "category": category,
            "payment_method": payment_method,
            "source": "sms",  # Distinguishes from manually-logged expenses
            "sms_metadata": {
                "sender": sender,
                "bank": parsed.get("bank"),
                "account_last4": parsed.get("account_last4"),
                "reference_id": parsed.get("reference_id"),
                "raw_sms": parsed["raw_sms"],
            },
            "occurred_at": (
                datetime.fromisoformat(parsed["timestamp"])
                if parsed.get("timestamp")
                else now
            ),
            "created_at": now,
            "updated_at": now,
        }

        # 4. Duplicate check — reference_id, raw_sms, or same amount + merchant within 7 days
        ref_id = str(parsed.get("reference_id")).strip() if parsed.get("reference_id") else None
        raw_sms = str(parsed.get("raw_sms")).strip() if parsed.get("raw_sms") else None
        occurred_date = document["occurred_at"].strftime("%Y-%m-%d")

        or_conditions = []
        if ref_id:
            or_conditions.append({"sms_metadata.reference_id": ref_id})
            or_conditions.append({"sms_metadata.reference_id": {"$regex": f"^{re.escape(ref_id)}$", "$options": "i"}})
        if raw_sms:
            or_conditions.append({"sms_metadata.raw_sms": raw_sms})

        # Fuzzy match for same amount, merchant, and occurred date/window
        seven_days_ago = datetime.fromtimestamp(now.timestamp() - 7 * 86400, tz=timezone.utc)
        or_conditions.append({
            "amount": parsed["amount"],
            "description": {"$regex": f"^{re.escape(description)}$", "$options": "i"},
            "created_at": {"$gte": seven_days_ago},
        })

        duplicate = await get_collection("expenses").find_one({
            "user_id": user_id,
            "$or": or_conditions,
        })

        if duplicate:
            logger.info(
                "[SmsExpenseAgent] Duplicate SMS skipped: ₹%.2f at %s (Ref: %s)",
                parsed["amount"], description, ref_id or "N/A",
            )
            return {
                "success": False,
                "expense": None,
                "message": f"Duplicate SMS expense already logged (₹{parsed['amount']} at {description}).",
            }

        # 5. Insert (with DuplicateKeyError protection against concurrency race conditions)
        try:
            result = await get_collection("expenses").insert_one(document)
            document["_id"] = str(result.inserted_id)
        except DuplicateKeyError:
            logger.info(
                "[SmsExpenseAgent] Atomic duplicate key blocked for user %s: Ref: %s",
                user_id, ref_id or "N/A",
            )
            return {
                "success": False,
                "expense": None,
                "message": f"Duplicate SMS expense already logged (Ref: {ref_id or 'duplicate'}).",
            }

        logger.info(
            "[SmsExpenseAgent] Logged ₹%.2f at %s (category: %s) for user %s",
            parsed["amount"], description, category, user_id,
        )

        return {
            "success": True,
            "expense": {
                "_id": str(result.inserted_id),
                "amount": parsed["amount"],
                "description": description,
                "category": category,
                "payment_method": payment_method,
                "bank": parsed.get("bank"),
                "source": "sms",
                "occurred_at": document["occurred_at"].isoformat(),
            },
            "message": (
                f"✅ Auto-tracked: ₹{parsed['amount']:.0f} "
                f"at {description} ({category})"
            ),
        }

    async def get_sms_expenses(self, user_id: str, limit: int = 30) -> list[dict]:
        """Fetch recent SMS-auto-tracked expenses for the dashboard in descending order (newest first), deduplicated."""
        # Query more documents to allow in-memory deduplication of any historical duplicates
        documents = (
            await get_collection("expenses")
            .find({"user_id": user_id, "source": "sms"})
            .sort([("occurred_at", -1), ("created_at", -1), ("_id", -1)])
            .to_list(length=max(limit * 3, 100))
        )
        result = []
        seen_refs = set()
        seen_signatures = set()

        for doc in documents:
            doc["_id"] = str(doc["_id"])
            sms_meta = doc.get("sms_metadata") if isinstance(doc.get("sms_metadata"), dict) else {}
            ref_id = str(sms_meta.get("reference_id") or "").strip()
            
            occurred = doc.get("occurred_at") or doc.get("created_at")
            date_str = occurred.strftime("%Y-%m-%d") if hasattr(occurred, "strftime") else str(occurred)[:10]
            amount = round(float(doc.get("amount", 0)), 2)
            desc = str(doc.get("description", "")).strip().lower()
            sig = (amount, desc, date_str)

            is_dup = False
            if ref_id:
                if ref_id in seen_refs:
                    is_dup = True
                else:
                    seen_refs.add(ref_id)

            if not is_dup:
                if sig in seen_signatures:
                    is_dup = True
                else:
                    seen_signatures.add(sig)

            if is_dup:
                continue

            if "occurred_at" in doc and hasattr(doc["occurred_at"], "isoformat"):
                doc["occurred_at"] = doc["occurred_at"].isoformat()
            if "created_at" in doc and hasattr(doc["created_at"], "isoformat"):
                doc["created_at"] = doc["created_at"].isoformat()
            if "updated_at" in doc and hasattr(doc["updated_at"], "isoformat"):
                doc["updated_at"] = doc["updated_at"].isoformat()
            result.append(doc)
            if len(result) >= limit:
                break
        return result

    async def deduplicate_expenses(self, user_id: str) -> dict:
        """Find and remove all duplicate expenses for a user, keeping only 1 copy."""
        collection = get_collection("expenses")
        cursor = collection.find({"user_id": user_id}).sort([("created_at", 1), ("_id", 1)])
        all_expenses = await cursor.to_list(length=10000)

        seen_refs = set()
        seen_signatures = set()
        duplicate_ids = []

        for doc in all_expenses:
            doc_id = doc["_id"]
            sms_meta = doc.get("sms_metadata") if isinstance(doc.get("sms_metadata"), dict) else {}
            ref_id = sms_meta.get("reference_id")
            
            occurred = doc.get("occurred_at") or doc.get("created_at")
            date_str = occurred.strftime("%Y-%m-%d") if hasattr(occurred, "strftime") else str(occurred)[:10]
            amount = round(float(doc.get("amount", 0)), 2)
            desc = str(doc.get("description", "")).strip().lower()
            
            sig = (amount, desc, date_str)
            is_dup = False

            if ref_id and ref_id.strip():
                if ref_id.strip() in seen_refs:
                    is_dup = True
                else:
                    seen_refs.add(ref_id.strip())

            if not is_dup:
                if sig in seen_signatures:
                    is_dup = True
                else:
                    seen_signatures.add(sig)

            if is_dup:
                duplicate_ids.append(doc_id)

        deleted_count = 0
        if duplicate_ids:
            res = await collection.delete_many({"_id": {"$in": duplicate_ids}})
            deleted_count = res.deleted_count

        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleaned {deleted_count} duplicate expense{'s' if deleted_count != 1 else ''}.",
        }


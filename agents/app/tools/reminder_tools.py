import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.core.llm import LLMUnavailableError, generate_response
from app.core.mongodb import get_collection
from bson import ObjectId

logger = logging.getLogger(__name__)


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


async def parse_reminder_command(message: str, local_time: str) -> dict:
    """Uses LLM to extract the task description and calculate the exact execution time."""
    prompt = f"""Parse this reminder request into strict JSON.

Current Local Time Context: {local_time}

Extract the task to be reminded about, and the exact ISO-8601 datetime when the reminder should trigger.
If it's relative (e.g. "in 10 minutes", "tomorrow at 5pm"), calculate the exact future datetime.

JSON shape:
{{
  "operation": "schedule_reminder",
  "task": "drink water",
  "execute_at": "2026-05-01T14:30:00+05:30"
}}

Rules:
- Operation can be 'schedule_reminder', 'list_reminders', or 'cancel_reminder' (if they ask to delete a reminder).
- Provide 'task' as a short string.
- Provide 'execute_at' as a valid ISO-8601 datetime string with timezone offset.
- If no time is specified, default to 5 minutes from now.
- Return ONLY JSON. No markdown.

User message: "{message}"
"""
    try:
        response_text = await generate_response(
            prompt,
            system_prompt="You are a precise time-parsing engine. Return strict JSON only.",
            temperature=0,
        )
        data = _parse_json(response_text)
        return {
            "operation": data.get("operation", "schedule_reminder"),
            "task": data.get("task", "Reminder"),
            "execute_at": data.get("execute_at"),
        }
    except LLMUnavailableError:
        # Fallback
        return {
            "operation": "schedule_reminder",
            "task": message.replace("remind me to", "").strip(),
            "execute_at": None,
        }


# ── MongoDB Operations ──────────────────────────────────────────────────

async def create_reminder(user_id: str, task: str, execute_at: str) -> Dict:
    collection = get_collection("reminders")
    
    # Normalize execute_at to UTC string to ensure correct DB string comparison
    try:
        dt = datetime.fromisoformat(execute_at)
        utc_execute_at = dt.astimezone(timezone.utc).isoformat()
    except Exception:
        utc_execute_at = execute_at

    doc = {
        "user_id": user_id,
        "task": task,
        "execute_at": utc_execute_at,
        "status": "pending",  # pending, triggered, acknowledged
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await collection.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc


async def get_active_reminders(user_id: str) -> List[Dict]:
    """Returns all pending or triggered (unacknowledged) reminders."""
    collection = get_collection("reminders")
    cursor = collection.find({"user_id": user_id, "status": {"$in": ["pending", "triggered"]}}).sort("execute_at", 1)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


async def acknowledge_reminder(user_id: str, reminder_id: str) -> bool:
    collection = get_collection("reminders")
    res = await collection.update_one(
        {"_id": ObjectId(reminder_id), "user_id": user_id},
        {"$set": {"status": "acknowledged"}}
    )
    return res.modified_count > 0


async def cancel_all_reminders(user_id: str) -> int:
    collection = get_collection("reminders")
    res = await collection.update_many(
        {"user_id": user_id, "status": "pending"},
        {"$set": {"status": "cancelled"}}
    )
    return res.modified_count

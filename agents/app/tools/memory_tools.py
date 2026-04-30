import json
import re

from app.core.llm import LLMUnavailableError, generate_response

MEMORY_OPERATIONS = {
    "save_memory",
    "recall_memory",
    "delete_memory",
    "list_memories",
    "clear_memories",
}

MEMORY_CATEGORIES = {
    "personal", "diet", "finance", "health",
    "preferences", "goals", "work", "other",
}


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def normalize_memory_command(payload: dict) -> dict:
    operation = payload.get("operation")
    if operation not in MEMORY_OPERATIONS:
        operation = "list_memories"
    category = payload.get("category", "other")
    if category not in MEMORY_CATEGORIES:
        category = "other"
    return {
        "operation": operation,
        "key": str(payload.get("key") or "").strip().lower().replace(" ", "_"),
        "value": str(payload.get("value") or "").strip(),
        "category": category,
        "query": str(payload.get("query") or "").strip().lower(),
    }


async def parse_memory_command(message: str) -> dict:
    prompt = f"""Parse this personal memory management request into strict JSON.

Allowed operations: {", ".join(sorted(MEMORY_OPERATIONS))}
Allowed categories: {", ".join(sorted(MEMORY_CATEGORIES))}

JSON shape:
{{
  "operation": "save_memory",
  "key": "diet",
  "value": "vegetarian",
  "category": "personal",
  "query": ""
}}

Rules:
- "remember / note / store / save that I ..." → save_memory
- "what do you know / my profile / show / list memories" → list_memories
- "forget / delete / remove my X" → delete_memory
- "what is my X / recall X" → recall_memory
- "clear all / erase everything" → clear_memories
- key: short snake_case label (diet, monthly_salary, gym_time, water_goal)
- value: the fact itself ("vegetarian", "50000", "7am")
- category: personal | diet | finance | health | preferences | goals | work | other
- query: for recall/delete only — the key to look up
- Return ONLY JSON. No markdown.

Examples:
"Remember I am vegetarian" → {{"operation":"save_memory","key":"diet","value":"vegetarian","category":"diet","query":""}}
"My salary is 50000" → {{"operation":"save_memory","key":"monthly_salary","value":"50000","category":"finance","query":""}}
"I gym at 7am" → {{"operation":"save_memory","key":"gym_time","value":"7am","category":"health","query":""}}
"What do you know about me?" → {{"operation":"list_memories","key":"","value":"","category":"other","query":""}}
"Forget my diet" → {{"operation":"delete_memory","key":"","value":"","category":"other","query":"diet"}}

User message: {message}
"""
    try:
        response_text = await generate_response(
            prompt,
            system_prompt="You parse personal memory commands for Jarvis. Return strict JSON only.",
            temperature=0,
        )
        return normalize_memory_command(_parse_json(response_text))
    except LLMUnavailableError:
        msg = message.lower()
        if any(w in msg for w in ["what do you know", "my profile", "list", "show memories"]):
            return normalize_memory_command({"operation": "list_memories"})
        return normalize_memory_command({"operation": "list_memories"})

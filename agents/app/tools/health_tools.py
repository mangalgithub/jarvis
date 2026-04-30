import json
import re
from datetime import UTC, datetime, time, timedelta, timezone

from app.core.llm import LLMUnavailableError, generate_response

LOCAL_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

HEALTH_OPERATIONS = {
    "log_water", "log_workout", "log_nutrition",
    "query_water", "query_workouts", "query_nutrition",
    "set_water_goal", "set_nutrition_goal", "daily_summary",
}

WORKOUT_TYPES = {
    "gym", "run", "walk", "yoga", "swim", "cycling", "cardio",
    "strength", "hiit", "pilates", "boxing", "cricket", "football",
    "basketball", "tennis", "badminton", "other",
}


def now_local() -> datetime:
    return datetime.now(LOCAL_TIMEZONE)


def local_day_bounds(day: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(day.date(), time.min, tzinfo=LOCAL_TIMEZONE)
    end = datetime.combine(day.date(), time.max, tzinfo=LOCAL_TIMEZONE)
    return start.astimezone(UTC), end.astimezone(UTC)


def resolve_health_date_range(message: str) -> tuple[str, datetime, datetime]:
    normalized = message.lower()
    current = now_local()
    if "yesterday" in normalized:
        start, end = local_day_bounds(current - timedelta(days=1))
        return "yesterday", start, end
    if "week" in normalized:
        start_local = datetime.combine(
            (current - timedelta(days=current.weekday())).date(),
            time.min, tzinfo=LOCAL_TIMEZONE,
        )
        return "this week", start_local.astimezone(UTC), current.astimezone(UTC)
    if "month" in normalized:
        start = datetime(current.year, current.month, 1, tzinfo=LOCAL_TIMEZONE)
        return "this month", start.astimezone(UTC), current.astimezone(UTC)
    start, end = local_day_bounds(current)
    return "today", start, end


def normalize_workout_type(raw: str | None) -> str:
    if not raw:
        return "other"
    normalized = raw.lower().strip()
    for wtype in WORKOUT_TYPES:
        if wtype in normalized:
            return wtype
    return "other"


def extract_water_glasses(text: str) -> float | None:
    """Regex fallback — extract water amount in glasses."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:glass(?:es)?|cup(?:s)?)", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:l|liter(?:s)?|litre(?:s)?)\b", text, re.IGNORECASE)
    if m:
        return float(m.group(1)) * 4  # 1 litre ≈ 4 glasses
    m = re.search(r"(\d+(?:\.\d+)?)\s*ml\b", text, re.IGNORECASE)
    if m:
        return float(m.group(1)) / 250  # 250 ml = 1 glass
    return None


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def normalize_health_command(payload: dict) -> dict:
    operation = payload.get("operation")
    if operation not in HEALTH_OPERATIONS:
        operation = "daily_summary"
    return {
        "operation": operation,
        "water": payload.get("water") if isinstance(payload.get("water"), dict) else {},
        "workout": payload.get("workout") if isinstance(payload.get("workout"), dict) else {},
        "nutrition": payload.get("nutrition") if isinstance(payload.get("nutrition"), dict) else {},
        "goal": payload.get("goal") if isinstance(payload.get("goal"), dict) else {},
    }


async def parse_health_command(message: str) -> dict:
    current_date = now_local().date().isoformat()
    prompt = f"""You are Jarvis's health parser. Parse the user's message into strict JSON.
Today is {current_date} (Asia/Kolkata).

Allowed operations: {", ".join(sorted(HEALTH_OPERATIONS))}

JSON shape:
{{
  "operation": "log_nutrition",
  "water": {{"glasses": 3, "liters": 0.75}},
  "workout": {{"type": "gym", "duration_minutes": 45, "calories_burned": 300, "notes": "leg day"}},
  "nutrition": {{"meal": "pizza", "calories": 800, "protein": 35, "carbs": 90, "fat": 30}},
  "goal": {{"water_glasses": 8, "calories": 2000, "protein": 150}}
}}

CRITICAL RULE — Estimating nutrition from food names:
If the user mentions a food item WITHOUT exact numbers, ESTIMATE typical values:
- 1 pizza (whole, medium) ≈ 800 cal / 35g protein / 90g carbs / 28g fat
- 1 slice of pizza ≈ 285 cal / 12g protein
- 1 burger ≈ 550 cal / 30g protein
- 1 plate biryani ≈ 500 cal / 25g protein
- 1 roti/chapati ≈ 80 cal / 3g protein
- 1 bowl dal ≈ 150 cal / 9g protein
- 1 bowl paneer curry ≈ 300 cal / 18g protein
- 1 bowl pasta ≈ 400 cal / 15g protein
- 1 egg ≈ 70 cal / 6g protein
- 1 banana ≈ 90 cal / 1g protein
- 1 cup oats ≈ 300 cal / 10g protein
- 1 glass milk ≈ 120 cal / 6g protein
NEVER return null for calories or protein when a food name is present. Always estimate.
Set "meal" to the food name (e.g. "pizza", "biryani", "oats with milk").

Operation routing:
- drank/water/glass → log_water
- gym/run/workout/exercise/yoga/cardio → log_workout
- eat/ate/eating/had/having + any food name → log_nutrition
- explicit calories or protein numbers → log_nutrition
- how much water → query_water
- workout history/stats → query_workouts
- calories this week/today → query_nutrition
- set water goal → set_water_goal
- set calorie/protein goal → set_nutrition_goal
- health summary/overview → daily_summary

Return ONLY JSON. No markdown. No explanation.
User message: {message}
"""
    try:
        response_text = await generate_response(
            prompt,
            system_prompt=(
                "You are a health data parser for Jarvis. "
                "Return strict JSON only. "
                "When a food is named, ALWAYS estimate calories and protein."
            ),
            temperature=0,
        )
        return normalize_health_command(_parse_json(response_text))
    except LLMUnavailableError:
        glasses = extract_water_glasses(message)
        if glasses:
            return normalize_health_command({"operation": "log_water", "water": {"glasses": glasses}})
        return normalize_health_command({"operation": "daily_summary"})


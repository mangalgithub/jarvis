import json
import re
from datetime import UTC, datetime, time, timedelta, timezone
from app.core.llm import LLMUnavailableError, generate_response

LOCAL_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

# --- ELITE NUTRITION DATABASE (V4) ---
# Format: "key": {"serving_weight": grams, "cal_per_100g": cal, "pro_per_100g": pro, "fat_per_100g": fat}
# We use dish-level macros, not raw ingredient macros.
FOOD_DB = {
    # Composite Dishes (Dish-level macros)
    "chicken curry": {"serving_weight": 200, "cal_per_100g": 130, "pro_per_100g": 10.0, "fat_per_100g": 7.0},
    "mutton curry": {"serving_weight": 200, "cal_per_100g": 180, "pro_per_100g": 12.0, "fat_per_100g": 12.0},
    "paneer curry": {"serving_weight": 200, "cal_per_100g": 160, "pro_per_100g": 7.0, "fat_per_100g": 12.0},
    "dal tadka": {"serving_weight": 150, "cal_per_100g": 90, "pro_per_100g": 4.5, "fat_per_100g": 4.0},
    "biryani": {"serving_weight": 350, "cal_per_100g": 160, "pro_per_100g": 6.5, "fat_per_100g": 7.0},
    "pizza": {"serving_weight": 100, "cal_per_100g": 266, "pro_per_100g": 11.0, "fat_per_100g": 10.0},
    "burger": {"serving_weight": 200, "cal_per_100g": 250, "pro_per_100g": 13.0, "fat_per_100g": 12.0},
    
    # Base Proteins (Cooked macros)
    "chicken": {"serving_weight": 100, "cal_per_100g": 165, "pro_per_100g": 31.0, "fat_per_100g": 3.6},
    "egg": {"serving_weight": 50, "cal_per_100g": 143, "pro_per_100g": 12.6, "fat_per_100g": 10.0},
    "fish": {"serving_weight": 150, "cal_per_100g": 120, "pro_per_100g": 20.0, "fat_per_100g": 4.0},
    
    # Staples
    "roti": {"serving_weight": 35, "cal_per_100g": 230, "pro_per_100g": 8.0, "fat_per_100g": 2.0},
    "rice": {"serving_weight": 150, "cal_per_100g": 130, "pro_per_100g": 2.7, "fat_per_100g": 0.3},
    "paratha": {"serving_weight": 80, "cal_per_100g": 300, "pro_per_100g": 6.0, "fat_per_100g": 15.0},
    
    # Snacks & Fruits
    "almond": {"serving_weight": 1.2, "cal_per_100g": 579, "pro_per_100g": 21.2, "fat_per_100g": 49.9},
    "walnut": {"serving_weight": 4.0, "cal_per_100g": 654, "pro_per_100g": 15.2, "fat_per_100g": 65.2},
    "banana": {"serving_weight": 110, "cal_per_100g": 89, "pro_per_100g": 1.1, "fat_per_100g": 0.3},
    "apple": {"serving_weight": 180, "cal_per_100g": 52, "pro_per_100g": 0.3, "fat_per_100g": 0.2},
    "milk": {"serving_weight": 250, "cal_per_100g": 62, "pro_per_100g": 3.2, "fat_per_100g": 3.3},
}

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

# Sort DB by key length (descending) to match "chicken curry" before "chicken"
SORTED_FOOD_KEYS = sorted(FOOD_DB.keys(), key=len, reverse=True)

def _calculate_elite_nutrition(items: list[dict]) -> dict:
    """Calculates nutrition with priority matching, composite dish logic, and density guardrails."""
    total_cal = 0.0
    total_pro = 0.0
    confidence = 1.0
    clarifications = []
    processed_names = []

    for item in items:
        # 1. Null-Safe Attribute Extraction
        raw_name = (item.get("name") or "").lower()
        unit = (item.get("unit") or "piece").lower()
        context = (item.get("context") or "home").lower()
        
        # 2. Safe Quantity Conversion
        raw_qty = item.get("qty")
        try:
            qty = float(raw_qty) if raw_qty is not None else 1.0
        except (ValueError, TypeError):
            qty = 1.0
            item["vague"] = True

        # 1. Priority-Based Entity Matching (Match long strings first)
        db_match = None
        for key in SORTED_FOOD_KEYS:
            if key in raw_name:
                db_match = FOOD_DB[key]
                break
        
        if not db_match:
            confidence *= 0.5
            clarifications.append(f"I don't have nutrition data for '{raw_name}'.")
            continue

        # 2. Dish-Specific Serving Resolution
        # If user says 'bowl', and we have a serving_weight, we use it as a base.
        base_weight = db_match["serving_weight"]
        if unit == "gram":
            total_weight = qty
        elif unit in ["bowl", "plate", "cup"]:
            total_weight = qty * base_weight # Assume 1 bowl = 1 standard serving for that food
        else:
            total_weight = qty * base_weight # Default to pieces/servings

        # 3. Context & Hidden Fat Layer (Scalar, not additive)
        # Restaurant food is usually 20-30% more calorie dense due to oils.
        multiplier = 1.25 if context == "restaurant" or "oily" in context else 1.0
        
        # 4. Deterministic Calculation
        cal = (total_weight / 100.0) * db_match["cal_per_100g"] * multiplier
        pro = (total_weight / 100.0) * db_match["pro_per_100g"]
        
        # 5. Protein Density Guardrail (The "Anti-Hallucination" check)
        # 100g of food almost never has more than 35g protein.
        protein_density = pro / total_weight if total_weight > 0 else 0
        if protein_density > 0.35:
            confidence *= 0.4
            clarifications.append(f"The protein in '{raw_name}' seems suspiciously high. Is this raw meat?")

        total_cal += cal
        total_pro += pro
        processed_names.append(f"{qty} {raw_name}")

    return {
        "meal": ", ".join(processed_names),
        "calories": round(total_cal, 1),
        "protein": round(total_pro, 1),
        "confidence": round(confidence, 2),
        "clarification": clarifications[0] if clarifications else None
    }

async def parse_health_command(message: str, user_memory: str = "") -> dict:
    current_date = now_local().date().isoformat()
    prompt = f"""You are Jarvis's elite health parser. Today: {current_date}
Extract entities into strict JSON.

Allowed Operations:
- log_nutrition: Use this for 'ate', 'had', 'eating', 'logged', or any mention of food/meals.
- log_water: Use for 'drank', 'water', 'glasses'.
- log_workout: Use for 'gym', 'run', 'workout'.
- query_nutrition/query_water/query_workouts: Use for 'how much', 'what did I eat', 'history'.
- daily_summary: Default if no action is found.

JSON Format (choose the one matching the operation):

For log_nutrition:
{{
  "operation": "log_nutrition",
  "nutrition": {{
    "items": [
      {{ "name": "chicken curry", "qty": 1, "unit": "bowl", "context": "restaurant", "vague": false }},
      {{ "name": "chicken", "qty": 1, "unit": "piece", "context": "home", "vague": true }}
    ]
  }}
}}

For log_workout:
{{
  "operation": "log_workout",
  "workout": {{
    "type": "gym",
    "duration_minutes": 60,
    "calories_burned": null,
    "notes": ""
  }}
}}

For log_water:
{{
  "operation": "log_water",
  "water": {{
    "glasses": 3,
    "liters": null
  }}
}}

RULES:
1. If the user mentions food (e.g., 'ate', 'had'), ALWAYS use "operation": "log_nutrition".
2. ONLY extract name, qty, unit, context.
3. **STRICT Vague Rule**: If the user uses vague words (e.g., 'some', 'a bit') instead of a number, set "qty": null and "vague": true.
4. **Clarification Override**: If the message contains "Clarification:", the ambiguity is now **RESOLVED**. Use the new info in the clarification to fill in any missing/null quantities and **SET "vague": false**.
5. If image analysis is present ('[IMAGE ANALYSIS: ...]'), extract those entities.

User message: {message}
"""
    try:
        response_text = await generate_response(
            prompt,
            system_prompt="Strict JSON extractor. No markdown. No chatter.",
            temperature=0,
        )
        payload = _parse_json(response_text)
        
        if not payload:
             return {"operation": "parse_error", "reply_override": "I couldn't quite parse that health command. Could you try rephrasing?"}

        if payload.get("operation") == "log_nutrition":
            items = payload.get("nutrition", {}).get("items", [])
            analysis = _calculate_elite_nutrition(items)
            
            # Check for vagueness in items
            any_vague = any(item.get("vague") is True for item in items)
            if any_vague:
                analysis["confidence"] *= 0.5
                analysis["clarification"] = "I caught that you had some food, but the quantity was a bit vague."

            if analysis["confidence"] < 0.6 or analysis["clarification"]:
                reason = analysis["clarification"] if analysis["clarification"] else "I'm a bit unsure about those portions."
                payload["reply_override"] = f"🤔 {reason} Please clarify so I can log it accurately."
                payload["operation"] = "ask_clarification"
            
            payload["nutrition"] = analysis
            
        return normalize_health_command(payload)
    except Exception as e:
        print(f"Health parse error: {e}")
        return {"operation": "error", "reply_override": "I encountered an error while processing your health data."}

def normalize_health_command(payload: dict) -> dict:
    return {
        "operation": payload.get("operation", "daily_summary"),
        "water": payload.get("water", {}),
        "workout": payload.get("workout", {}),
        "nutrition": payload.get("nutrition", {}),
        "reply_override": payload.get("reply_override")
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
        start_local = datetime.combine((current - timedelta(days=current.weekday())).date(), time.min, tzinfo=LOCAL_TIMEZONE)
        return "this week", start_local.astimezone(UTC), current.astimezone(UTC)
    start, end = local_day_bounds(current)
    return "today", start, end

def normalize_workout_type(raw: str | None) -> str:
    if not raw: return "other"
    for wtype in WORKOUT_TYPES:
        if wtype in raw.lower(): return wtype
    return "other"

def _parse_json(text: str) -> dict:
    """Robust JSON extraction using first and last brace boundaries."""
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1:
            return {}
        return json.loads(text[start:end+1])
    except:
        return {}

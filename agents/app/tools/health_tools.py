import json
import logging
import re
from datetime import UTC, datetime, time, timedelta, timezone

from app.core.config import settings
from app.core.llm import LLMUnavailableError, generate_response
from app.core.redis import get_redis
from app.core.mongodb import get_collection

_log = logging.getLogger(__name__)

LOCAL_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

# Cache TTL: 30 days (in seconds)
NUTRITION_CACHE_TTL = 30 * 24 * 60 * 60

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


# ── Nutrition Prediction Pipeline (Gemini + Redis) ─────────────────────────


def _cache_key(food_name: str) -> str:
    """Normalize food name into a Redis cache key."""
    return f"nutrition:{food_name.strip().lower().replace(' ', '_')}"


async def _get_cached_nutrition(food_name: str) -> dict | None:
    """Check Redis first, then MongoDB nutrition_knowledge collection."""
    key = _cache_key(food_name)

    # 1. Redis check
    redis = await get_redis()
    if redis:
        try:
            cached = await redis.get(key)
            if cached:
                data = json.loads(cached)
                print(f"⚡ [CACHE HIT] Redis → {food_name}: {data.get('cal_per_serving')} cal, {data.get('pro_per_serving')}g pro per serving")
                return data
        except Exception as exc:
            _log.warning("Redis GET failed: %s", exc)

    # 2. MongoDB fallback
    doc = await get_collection("nutrition_knowledge").find_one(
        {"food_name": food_name.strip().lower()}
    )
    if doc:
        print(f"📦 [CACHE HIT] MongoDB → {food_name}: {doc.get('cal_per_serving')} cal, {doc.get('pro_per_serving')}g pro per serving")
        data = {
            "cal_per_serving": doc["cal_per_serving"],
            "pro_per_serving": doc["pro_per_serving"],
            "fat_per_serving": doc.get("fat_per_serving", 0),
            "carbs_per_serving": doc.get("carbs_per_serving", 0),
            "serving_weight_g": doc["serving_weight_g"],
            "serving_unit": doc.get("serving_unit", "serving"),
        }
        # Re-populate Redis
        if redis:
            try:
                await redis.set(key, json.dumps(data), ex=NUTRITION_CACHE_TTL)
            except Exception:
                pass
        return data

    return None


async def _cache_nutrition(food_name: str, data: dict) -> None:
    """Save a reliable prediction to Redis (30-day TTL) and MongoDB (permanent)."""
    key = _cache_key(food_name)
    normalized_name = food_name.strip().lower()

    # Redis
    redis = await get_redis()
    if redis:
        try:
            await redis.set(key, json.dumps(data), ex=NUTRITION_CACHE_TTL)
            _log.info("Redis SET: %s", key)
        except Exception as exc:
            _log.warning("Redis SET failed: %s", exc)

    # MongoDB — upsert into nutrition_knowledge
    await get_collection("nutrition_knowledge").update_one(
        {"food_name": normalized_name},
        {"$set": {
            **data,
            "food_name": normalized_name,
            "updated_at": datetime.now(UTC),
        }},
        upsert=True,
    )
    _log.info("MongoDB SAVED: %s", normalized_name)


def _is_prediction_reliable(prediction: dict) -> bool:
    """Validate LLM nutrition prediction with sanity guardrails."""
    cal = prediction.get("cal_per_serving", 0)
    pro = prediction.get("pro_per_serving", 0)
    serving_g = prediction.get("serving_weight_g", 0)

    # Basic range checks
    if cal <= 0 or cal > 5000:
        _log.warning("Guardrail FAIL: calories %s out of range", cal)
        return False

    if pro < 0 or pro > 200:
        _log.warning("Guardrail FAIL: protein %sg out of range", pro)
        return False

    if serving_g <= 0:
        _log.warning("Guardrail FAIL: serving weight %sg invalid", serving_g)
        return False

    # Protein cannot exceed calories / 4 (1g protein = 4 cal)
    if pro > 0 and cal > 0 and pro > (cal / 4) * 1.1:  # 10% tolerance
        _log.warning("Guardrail FAIL: protein %sg exceeds calorie-protein ratio (cal=%s)", pro, cal)
        return False

    # Protein density check: > 35g protein per 100g is suspicious
    if serving_g > 0:
        density = (pro / serving_g) * 100
        if density > 35:
            _log.warning("Guardrail FAIL: protein density %.1f g/100g too high", density)
            return False

    return True


async def _predict_single_item_nutrition(food_name: str, qty: float, unit: str, context: str) -> dict:
    """
    Predict nutrition for a single food item.
    Pipeline: Redis Cache → MongoDB → Gemini LLM → Validate → Cache
    """
    normalized_name = food_name.strip().lower()

    # 1. Try cache first (per-serving base data)
    cached = await _get_cached_nutrition(normalized_name)
    if cached:
        result = _apply_quantity(cached, qty, unit, context)
        print(f"   → Final: {qty:.0f}× {unit} = {result['calories']} cal, {result['protein']}g pro")
        return result

    # 2. Cache miss → ask Gemini
    print(f"🔍 [CACHE MISS] {normalized_name} → querying Gemini...")
    from google import genai
    from app.core.config import settings as cfg

    if not cfg.google_api_key:
        _log.error("GOOGLE_API_KEY not set, cannot predict nutrition")
        return {"calories": 0, "protein": 0, "meal": normalized_name, "source": "error"}

    prompt = f"""You are a professional nutritionist AI. Estimate the nutritional content for this food item.

Food: {normalized_name}
Serving: 1 standard serving

Return ONLY valid JSON (no markdown, no commentary):
{{
  "cal_per_serving": <calories for 1 standard serving>,
  "pro_per_serving": <protein in grams for 1 standard serving>,
  "fat_per_serving": <fat in grams for 1 standard serving>,
  "carbs_per_serving": <carbs in grams for 1 standard serving>,
  "serving_weight_g": <weight in grams for 1 standard serving>,
  "serving_unit": "<most natural unit: piece, bowl, plate, cup, glass, slice, etc>"
}}

Guidelines:
- Use COOKED/PREPARED values, not raw.
- For Indian dishes (dal, biryani, curry), use standard restaurant portion sizes.
- For items like roti/chapati, 1 piece ≈ 35g. For rice, 1 plate ≈ 150g.
- For fruits, use 1 medium-sized piece.
- Be accurate — real nutritionists will verify this data.
"""

    try:
        client = genai.Client(api_key=cfg.google_api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        if not response or not response.text:
            _log.error("Gemini returned empty response for: %s", normalized_name)
            return {"calories": 0, "protein": 0, "meal": normalized_name, "source": "error"}

        prediction = _parse_json(response.text)
        if not prediction:
            _log.error("Failed to parse Gemini response: %s", response.text[:200])
            return {"calories": 0, "protein": 0, "meal": normalized_name, "source": "error"}

        # 3. Validate reliability
        print(f"🤖 [GEMINI] {normalized_name}: {prediction.get('cal_per_serving')} cal, {prediction.get('pro_per_serving')}g pro, {prediction.get('serving_weight_g')}g serving")
        if _is_prediction_reliable(prediction):
            # 4. Cache the reliable base data
            await _cache_nutrition(normalized_name, prediction)
            print(f"✅ [CACHED] {normalized_name} → Redis (30d TTL) + MongoDB")
        else:
            print(f"⚠️ [NOT CACHED] {normalized_name} → failed reliability check")

        # 5. Apply quantity multipliers
        result = _apply_quantity(prediction, qty, unit, context)
        print(f"   → Final: {qty:.0f}× {unit} ({context}) = {result['calories']} cal, {result['protein']}g pro")
        return result

    except Exception as exc:
        _log.error("Gemini nutrition prediction failed: %s", exc)
        return {"calories": 0, "protein": 0, "meal": normalized_name, "source": "error"}


def _apply_quantity(base_data: dict, qty: float, unit: str, context: str) -> dict:
    """Multiply per-serving base data by quantity, unit, and context."""
    cal_per = base_data.get("cal_per_serving", 0)
    pro_per = base_data.get("pro_per_serving", 0)
    fat_per = base_data.get("fat_per_serving", 0)
    carbs_per = base_data.get("carbs_per_serving", 0)
    serving_g = base_data.get("serving_weight_g", 100)

    # Unit-based multiplier
    if unit == "gram":
        # User specified grams directly: scale relative to one serving
        multiplier = qty / serving_g if serving_g > 0 else 1.0
    else:
        # pieces, bowls, plates, cups — each = 1 serving
        multiplier = qty

    # Context multiplier (restaurant food has more oil/butter)
    context_mult = 1.25 if context in ("restaurant", "outside") or "oily" in context else 1.0

    return {
        "calories": round(cal_per * multiplier * context_mult, 1),
        "protein": round(pro_per * multiplier, 1),
        "fat": round(fat_per * multiplier * context_mult, 1),
        "carbs": round(carbs_per * multiplier, 1),
        "source": "cached" if True else "llm",  # tag for debugging
    }


async def _predict_nutrition_llm(items: list[dict]) -> dict:
    """
    Main entry point: predict nutrition for a list of food items.
    Each item goes through Cache → MongoDB → Gemini pipeline independently.
    """
    total_cal = 0.0
    total_pro = 0.0
    total_fat = 0.0
    total_carbs = 0.0
    processed_names = []
    confidence = 1.0
    clarifications = []

    for item in items:
        raw_name = (item.get("name") or "").strip()
        if not raw_name:
            continue

        unit = (item.get("unit") or "piece").lower()
        context = (item.get("context") or "home").lower()

        # Safe quantity conversion
        raw_qty = item.get("qty")
        try:
            qty = float(raw_qty) if raw_qty is not None else 1.0
        except (ValueError, TypeError):
            qty = 1.0
            item["vague"] = True

        result = await _predict_single_item_nutrition(raw_name, qty, unit, context)

        if result.get("source") == "error":
            confidence *= 0.5
            clarifications.append(f"Could not estimate nutrition for '{raw_name}'.")
            continue

        total_cal += result.get("calories", 0)
        total_pro += result.get("protein", 0)
        total_fat += result.get("fat", 0)
        total_carbs += result.get("carbs", 0)
        processed_names.append(f"{qty:.0f} {raw_name}")

    return {
        "meal": ", ".join(processed_names) if processed_names else "meal",
        "calories": round(total_cal, 1),
        "protein": round(total_pro, 1),
        "fat": round(total_fat, 1),
        "carbs": round(total_carbs, 1),
        "confidence": round(confidence, 2),
        "clarification": clarifications[0] if clarifications else None,
    }


# ── Health Command Parsing (LLM) ──────────────────────────────────────────


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
      {{ "name": "roti", "qty": 2, "unit": "piece", "context": "home", "vague": false }}
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
6. **Quantity Scoping**: A number ONLY applies to the food item it directly precedes. Example: "ate 2 rotis and dal" → roti qty=2, dal qty=1 (NOT 2). Do NOT propagate quantities across items.

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
            analysis = await _predict_nutrition_llm(items)

            # Only trigger clarification if the prediction itself failed
            # (e.g., unknown food items). Missing quantity defaults to 1 serving.
            if analysis["confidence"] < 0.6:
                reason = analysis["clarification"] if analysis["clarification"] else "I'm a bit unsure about those portions."
                payload["reply_override"] = f"🤔 {reason} Please clarify so I can log it accurately."
                payload["operation"] = "ask_clarification"
            
            payload["nutrition"] = analysis
            
        return normalize_health_command(payload)
    except Exception as e:
        _log.error("Health parse error: %s", e, exc_info=True)
        return {"operation": "error", "reply_override": "I encountered an error while processing your health data."}


def normalize_health_command(payload: dict) -> dict:
    return {
        "operation": payload.get("operation", "daily_summary"),
        "water": payload.get("water", {}),
        "workout": payload.get("workout", {}),
        "nutrition": payload.get("nutrition", {}),
        "reply_override": payload.get("reply_override")
    }


# ── Date / Time Utilities ─────────────────────────────────────────────────


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

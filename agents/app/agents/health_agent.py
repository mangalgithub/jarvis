from datetime import UTC, datetime, timedelta

from bson import ObjectId

from app.core.mongodb import get_collection
from app.tools.health_tools import (
    local_day_bounds,
    normalize_workout_type,
    now_local,
    parse_health_command,
    resolve_health_date_range,
)

DEFAULT_WATER_GOAL = 8      # glasses/day
DEFAULT_CALORIE_GOAL = 2000  # kcal/day
DEFAULT_PROTEIN_GOAL = 150   # grams/day


class HealthAgent:
    name = "health"

    async def run(self, context: dict) -> dict:
        message = context.get("message", "")
        user_id = context.get("user_id", "default-user")
        user_memory = context.get("user_memory", "")
        command = await parse_health_command(message, user_memory)
        operation = command["operation"]

        try:
            if operation == "log_water":
                return await self._log_water(user_id, command)
            if operation == "log_workout":
                return await self._log_workout(user_id, command)
            if operation == "log_nutrition":
                return await self._log_nutrition(user_id, command)
            if operation == "query_water":
                return await self._query_water(user_id, message)
            if operation == "query_workouts":
                return await self._query_workouts(user_id, message)
            if operation == "query_nutrition":
                return await self._query_nutrition(user_id, message)
            if operation == "set_water_goal":
                return await self._set_water_goal(user_id, command)
            if operation == "set_nutrition_goal":
                return await self._set_nutrition_goal(user_id, command)
            return await self._daily_summary(user_id)
        except Exception as error:
            return {
                "reply": "Health data could not be saved. Check that MongoDB is running.",
                "actions": [{"type": "health_operation_failed", "operation": operation, "error": str(error)}],
            }

    # ── Water ──────────────────────────────────────────────────────────────

    async def _log_water(self, user_id: str, command: dict) -> dict:
        water = command.get("water") or {}
        glasses = water.get("glasses")
        liters = water.get("liters")

        if glasses is None and liters is None:
            return {
                "reply": "I couldn't find a water amount. Try: I drank 3 glasses of water.",
                "actions": [{"type": "water_parse_empty"}],
            }

        if glasses is None:
            glasses = round(float(liters) * 4, 1)
        if liters is None:
            liters = round(float(glasses) / 4, 2)

        now = datetime.now(UTC)
        await get_collection("water_logs").insert_one({
            "user_id": user_id, "glasses": float(glasses),
            "liters": float(liters), "logged_at": now, "created_at": now,
        })
        today_total = await self._water_today(user_id)
        goal = await self._get_water_goal(user_id)
        return {
            "reply": (
                f"Logged {glasses:.0f} glass{'es' if glasses != 1 else ''} of water. "
                f"Today: {today_total:.0f}/{goal:.0f} glasses 💧"
            ),
            "actions": [{"type": "water_logged", "glasses": glasses, "today_total": today_total, "goal": goal}],
        }

    async def _query_water(self, user_id: str, message: str) -> dict:
        period, start, end = resolve_health_date_range(message)
        docs = await get_collection("water_logs").find(
            self._date_query(user_id, start, end)
        ).to_list(length=200)
        total = sum(d.get("glasses", 0) for d in docs)
        goal = await self._get_water_goal(user_id)
        return {
            "reply": f"You drank {total:.0f} glasses of water {period}. Daily goal: {goal:.0f} glasses.",
            "actions": [{"type": "water_query_result", "period": period, "total_glasses": total, "goal": goal}],
        }

    async def _set_water_goal(self, user_id: str, command: dict) -> dict:
        glasses = (command.get("goal") or {}).get("water_glasses")
        if glasses is None:
            return {"reply": "Tell me the goal, e.g. set water goal 8 glasses.", "actions": []}
        await get_collection("health_goals").update_one(
            {"user_id": user_id},
            {"$set": {"water_glasses": float(glasses), "updated_at": datetime.now(UTC)}},
            upsert=True,
        )
        return {
            "reply": f"Water goal set to {glasses:.0f} glasses per day. 💧",
            "actions": [{"type": "water_goal_set", "glasses": glasses}],
        }

    # ── Workout ────────────────────────────────────────────────────────────

    async def _log_workout(self, user_id: str, command: dict) -> dict:
        workout = command.get("workout") or {}
        duration = workout.get("duration_minutes")
        if duration is None:
            return {
                "reply": "Tell me the duration, e.g. did 45 min gym.",
                "actions": [{"type": "workout_parse_empty"}],
            }
        now = datetime.now(UTC)
        doc = {
            "user_id": user_id,
            "type": normalize_workout_type(workout.get("type")),
            "duration_minutes": float(duration),
            "calories_burned": float(workout.get("calories_burned") or 0),
            "notes": workout.get("notes") or "",
            "logged_at": now, "created_at": now,
        }
        result = await get_collection("workout_logs").insert_one(doc)
        cal_text = f" ({doc['calories_burned']:.0f} cal burned)" if doc["calories_burned"] else ""
        return {
            "reply": f"Logged {doc['duration_minutes']:.0f} min {doc['type']}{cal_text}. Keep it up! 💪",
            "actions": [{"type": "workout_logged", "workout_id": str(result.inserted_id)}],
        }

    async def _query_workouts(self, user_id: str, message: str) -> dict:
        period, start, end = resolve_health_date_range(message)
        docs = await get_collection("workout_logs").find(
            self._date_query(user_id, start, end)
        ).sort("logged_at", -1).to_list(length=50)
        if not docs:
            return {"reply": f"No workouts logged for {period}.", "actions": [{"type": "workout_query_result", "workouts": []}]}
        total_min = sum(d.get("duration_minutes", 0) for d in docs)
        lines = ", ".join(f"{d['type']} {d['duration_minutes']:.0f}min" for d in docs[:5])
        return {
            "reply": f"{period.title()} workouts — {len(docs)} sessions, {total_min:.0f} min total: {lines}.",
            "actions": [{"type": "workout_query_result", "period": period, "workouts": self._serialize(docs)}],
        }

    # ── Nutrition ──────────────────────────────────────────────────────────

    async def _log_nutrition(self, user_id: str, command: dict) -> dict:
        n = command.get("nutrition") or {}
        calories = n.get("calories")
        protein = n.get("protein")
        if calories is None and protein is None:
            return {
                "reply": "Tell me calories or protein, e.g. ate 600 calories 40g protein for lunch.",
                "actions": [{"type": "nutrition_parse_empty"}],
            }
        now = datetime.now(UTC)
        doc = {
            "user_id": user_id,
            "meal": n.get("meal") or "meal",
            "calories": float(calories or 0),
            "protein": float(protein or 0),
            "carbs": float(n.get("carbs") or 0),
            "fat": float(n.get("fat") or 0),
            "logged_at": now, "created_at": now,
        }
        result = await get_collection("nutrition_logs").insert_one(doc)
        today_cal = await self._sum_today(user_id, "nutrition_logs", "calories")
        today_pro = await self._sum_today(user_id, "nutrition_logs", "protein")
        goals = await self._get_nutrition_goals(user_id)
        return {
            "reply": (
                f"Logged {doc['meal']}: {doc['calories']:.0f} cal, {doc['protein']:.0f}g protein. "
                f"Today: {today_cal:.0f}/{goals['calories']:.0f} cal | "
                f"{today_pro:.0f}/{goals['protein']:.0f}g protein."
            ),
            "actions": [{"type": "nutrition_logged", "nutrition_id": str(result.inserted_id),
                         "today_calories": today_cal, "today_protein": today_pro, "goals": goals}],
        }

    async def _query_nutrition(self, user_id: str, message: str) -> dict:
        period, start, end = resolve_health_date_range(message)
        docs = await get_collection("nutrition_logs").find(
            self._date_query(user_id, start, end)
        ).to_list(length=200)
        total_cal = sum(d.get("calories", 0) for d in docs)
        total_pro = sum(d.get("protein", 0) for d in docs)
        goals = await self._get_nutrition_goals(user_id)
        return {
            "reply": f"{period.title()} nutrition: {total_cal:.0f} cal, {total_pro:.0f}g protein. Daily goal: {goals['calories']:.0f} cal, {goals['protein']:.0f}g protein.",
            "actions": [{"type": "nutrition_query_result", "period": period,
                         "total_calories": total_cal, "total_protein": total_pro, "goals": goals}],
        }

    async def _set_nutrition_goal(self, user_id: str, command: dict) -> dict:
        goal = command.get("goal") or {}
        updates = {}
        if goal.get("calories") is not None:
            updates["calorie_goal"] = float(goal["calories"])
        if goal.get("protein") is not None:
            updates["protein_goal"] = float(goal["protein"])
        if not updates:
            return {"reply": "Tell me your calorie or protein goal.", "actions": []}
        updates["updated_at"] = datetime.now(UTC)
        await get_collection("health_goals").update_one({"user_id": user_id}, {"$set": updates}, upsert=True)
        parts = []
        if "calorie_goal" in updates:
            parts.append(f"{updates['calorie_goal']:.0f} cal")
        if "protein_goal" in updates:
            parts.append(f"{updates['protein_goal']:.0f}g protein")
        return {"reply": f"Nutrition goals updated: {' & '.join(parts)} per day.", "actions": [{"type": "nutrition_goal_set"}]}

    # ── Daily Summary ──────────────────────────────────────────────────────

    async def _daily_summary(self, user_id: str) -> dict:
        start, end = local_day_bounds(now_local())
        water = await self._sum_today(user_id, "water_logs", "glasses")
        water_goal = await self._get_water_goal(user_id)
        cal = await self._sum_today(user_id, "nutrition_logs", "calories")
        pro = await self._sum_today(user_id, "nutrition_logs", "protein")
        n_goals = await self._get_nutrition_goals(user_id)
        workout_docs = await get_collection("workout_logs").find(
            self._date_query(user_id, start, end)
        ).to_list(length=20)
        w_min = sum(d.get("duration_minutes", 0) for d in workout_docs)

        return {
            "reply": (
                f"Today's health summary:\n"
                f"💧 Water: {water:.0f}/{water_goal:.0f} glasses\n"
                f"🔥 Calories: {cal:.0f}/{n_goals['calories']:.0f}\n"
                f"🥩 Protein: {pro:.0f}/{n_goals['protein']:.0f}g\n"
                f"🏋️ Workout: {w_min:.0f} min ({len(workout_docs)} session{'s' if len(workout_docs) != 1 else ''})"
            ),
            "actions": [{
                "type": "health_daily_summary",
                "water": {"today": water, "goal": water_goal},
                "nutrition": {"calories": cal, "protein": pro, "goals": n_goals},
                "workout": {"minutes_today": w_min, "sessions": len(workout_docs)},
            }],
        }

    # ── Dashboard helper ───────────────────────────────────────────────────

    async def get_dashboard_health(self, user_id: str) -> dict:
        import logging
        _log = logging.getLogger(__name__)

        # ── Water ─────────────────────────────────────────────────────────
        try:
            water = await self._sum_today(user_id, "water_logs", "glasses")
            water_goal = await self._get_water_goal(user_id)
        except Exception as exc:
            _log.error("health water query failed: %s", exc, exc_info=True)
            water, water_goal = 0.0, float(DEFAULT_WATER_GOAL)

        # ── Nutrition ──────────────────────────────────────────────────────
        try:
            cal = await self._sum_today(user_id, "nutrition_logs", "calories")
            pro = await self._sum_today(user_id, "nutrition_logs", "protein")
            n_goals = await self._get_nutrition_goals(user_id)
        except Exception as exc:
            _log.error("health nutrition query failed: %s", exc, exc_info=True)
            cal, pro = 0.0, 0.0
            n_goals = {"calories": float(DEFAULT_CALORIE_GOAL), "protein": float(DEFAULT_PROTEIN_GOAL)}

        # ── Workout ────────────────────────────────────────────────────────
        streak = 0
        last_workout_info = None
        try:
            last_workout = await get_collection("workout_logs").find_one(
                {"user_id": user_id}, sort=[("logged_at", -1)]
            )
            streak = await self._workout_streak(user_id)
            if last_workout:
                last_workout_info = {
                    "type": last_workout.get("type", "other"),
                    "duration_minutes": last_workout.get("duration_minutes", 0),
                    "logged_at": last_workout["logged_at"].isoformat()
                    if hasattr(last_workout.get("logged_at"), "isoformat")
                    else str(last_workout.get("logged_at", "")),
                }
        except Exception as exc:
            _log.error("health workout query failed: %s", exc, exc_info=True)

        return {
            "water": {
                "today": water,
                "goal": water_goal,
                "progress": min(round((water / water_goal) * 100, 1), 100) if water_goal else 0,
            },
            "nutrition": {
                "calories": {"today": cal, "goal": n_goals["calories"]},
                "protein": {"today": pro, "goal": n_goals["protein"]},
            },
            "workout": {
                "streak_days": streak,
                "last": last_workout_info,
            },
        }


    # ── Internal helpers ───────────────────────────────────────────────────

    async def _water_today(self, user_id: str) -> float:
        start, end = local_day_bounds(now_local())
        docs = await get_collection("water_logs").find(
            self._date_query(user_id, start, end)
        ).to_list(length=200)
        return sum(d.get("glasses", 0) for d in docs)

    async def _sum_today(self, user_id: str, collection: str, field: str) -> float:
        start, end = local_day_bounds(now_local())
        docs = await get_collection(collection).find(
            self._date_query(user_id, start, end)
        ).to_list(length=200)
        return sum(d.get(field, 0) for d in docs)

    async def _get_water_goal(self, user_id: str) -> float:
        doc = await get_collection("health_goals").find_one({"user_id": user_id})
        return float(doc.get("water_glasses", DEFAULT_WATER_GOAL)) if doc else DEFAULT_WATER_GOAL

    async def _get_nutrition_goals(self, user_id: str) -> dict:
        doc = await get_collection("health_goals").find_one({"user_id": user_id})
        return {
            "calories": float(doc.get("calorie_goal", DEFAULT_CALORIE_GOAL)) if doc else DEFAULT_CALORIE_GOAL,
            "protein": float(doc.get("protein_goal", DEFAULT_PROTEIN_GOAL)) if doc else DEFAULT_PROTEIN_GOAL,
        }

    async def _workout_streak(self, user_id: str) -> int:
        streak = 0
        day = now_local()
        for _ in range(30):
            start, end = local_day_bounds(day)
            count = await get_collection("workout_logs").count_documents(
                self._date_query(user_id, start, end)
            )
            if count > 0:
                streak += 1
                day -= timedelta(days=1)
            else:
                break
        return streak

    def _date_query(self, user_id: str, start: datetime, end: datetime) -> dict:
        return {
            "user_id": user_id,
            "$or": [
                {"logged_at": {"$gte": start, "$lte": end}},
                {"logged_at": {"$exists": False}, "created_at": {"$gte": start, "$lte": end}},
            ],
        }

    def _serialize(self, docs: list[dict]) -> list[dict]:
        result = []
        for doc in docs:
            result.append({
                k: str(v) if isinstance(v, (ObjectId, datetime)) else
                   v.isoformat() if hasattr(v, "isoformat") else v
                for k, v in doc.items()
            })
        return result

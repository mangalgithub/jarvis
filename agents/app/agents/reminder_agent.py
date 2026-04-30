import logging
from datetime import datetime, timedelta

from app.tools.finance_tools import now_local
from app.tools.reminder_tools import (
    cancel_all_reminders,
    create_reminder,
    get_active_reminders,
    parse_reminder_command,
)

logger = logging.getLogger(__name__)


class ReminderAgent:
    name = "reminder"

    async def run(self, context: dict) -> dict:
        message = context.get("message", "")
        user_id = context.get("user_id", "default-user")
        
        # Fast path for UI acknowledge button
        if message.startswith("acknowledge reminder "):
            reminder_id = message.replace("acknowledge reminder ", "").strip()
            return await self._acknowledge(user_id, reminder_id)

        local_time = now_local().strftime("%Y-%m-%dT%H:%M:%S%z")
        command = await parse_reminder_command(message, local_time)
        operation = command["operation"]

        try:
            if operation == "schedule_reminder":
                return await self._schedule(user_id, command)
            if operation == "list_reminders":
                return await self._list(user_id)
            if operation == "cancel_reminder":
                return await self._cancel(user_id)
            return await self._schedule(user_id, command)
        except Exception as exc:
            logger.error("[ReminderAgent] error in %s: %s", operation, exc, exc_info=True)
            return {
                "reply": f"Sorry, I couldn't handle that reminder right now. ({exc})",
                "actions": [{"type": "reminder_error", "error": str(exc)}],
            }

    async def _schedule(self, user_id: str, command: dict) -> dict:
        task = command["task"]
        execute_at = command["execute_at"]

        # Fallback if LLM failed to parse time
        if not execute_at:
            execute_at = (now_local() + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S%z")

        doc = await create_reminder(user_id, task, execute_at)

        try:
            # Try to format nice time
            dt = datetime.fromisoformat(execute_at)
            time_str = dt.strftime("%I:%M %p on %b %d")
        except:
            time_str = execute_at

        return {
            "reply": f"Got it! I will remind you to **{task}** at {time_str}.",
            "actions": [{"type": "reminder_scheduled", "reminder": doc}],
        }

    async def _list(self, user_id: str) -> dict:
        reminders = await get_active_reminders(user_id)
        if not reminders:
            return {"reply": "You have no active reminders.", "actions": []}

        lines = ["⏰ **Active Reminders**\n"]
        for r in reminders:
            try:
                dt = datetime.fromisoformat(r['execute_at'])
                t_str = dt.strftime("%I:%M %p (%b %d)")
            except:
                t_str = r['execute_at']
            status = "🔔 Triggered!" if r['status'] == 'triggered' else "⏳ Pending"
            lines.append(f"• **{r['task']}** at {t_str} — {status}")

        return {
            "reply": "\n".join(lines),
            "actions": [{"type": "reminders_list", "reminders": reminders}],
        }

    async def _cancel(self, user_id: str) -> dict:
        count = await cancel_all_reminders(user_id)
        return {
            "reply": f"Cancelled {count} pending reminders." if count else "No pending reminders to cancel.",
            "actions": [{"type": "reminders_cancelled", "count": count}],
        }

    async def _acknowledge(self, user_id: str, reminder_id: str) -> dict:
        from app.tools.reminder_tools import acknowledge_reminder
        success = await acknowledge_reminder(user_id, reminder_id)
        return {
            "reply": "Reminder dismissed.",
            "actions": [{"type": "reminder_acknowledged", "success": success}],
        }

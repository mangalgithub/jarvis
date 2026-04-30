import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bson import ObjectId

from app.api.routes.websockets import manager as ws_manager
from app.core.mongodb import get_collection

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_reminders():
    """Polls MongoDB for pending reminders that are due and broadcasts them via WebSocket."""
    try:
        collection = get_collection("reminders")
        now_str = datetime.now(timezone.utc).isoformat()

        # Find pending reminders where execute_at <= now
        cursor = collection.find({
            "status": "pending",
            "execute_at": {"$lte": now_str}
        })

        reminders_to_trigger = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            reminders_to_trigger.append(doc)

        for r in reminders_to_trigger:
            logger.info("[scheduler] Triggering reminder: %s", r["task"])
            
            # Update status to triggered
            await collection.update_one(
                {"_id": ObjectId(r["_id"])},
                {"$set": {"status": "triggered"}}
            )

            # Broadcast via WebSocket
            message = {
                "type": "reminder_triggered",
                "reminder": r
            }
            await ws_manager.broadcast_to_user(r["user_id"], message)

    except Exception as exc:
        logger.error("[scheduler] Error checking reminders: %s", exc)


def start_scheduler():
    if not scheduler.running:
        # Run every 10 seconds
        scheduler.add_job(check_reminders, 'interval', seconds=10)
        scheduler.start()
        logger.info("[scheduler] Started reminder polling scheduler.")

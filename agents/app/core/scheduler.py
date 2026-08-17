import logging
import os
from datetime import datetime, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bson import ObjectId

from app.api.routes.websockets import manager as ws_manager
from app.core.mongodb import get_collection

logger = logging.getLogger(__name__)

# The public URL of THIS Space — set it as an env var on HuggingFace.
# e.g. https://lagnam-jarvis-agents.hf.space
_SELF_URL = os.getenv("SPACE_HOST", "").strip().rstrip("/")

scheduler = AsyncIOScheduler()


async def check_reminders():
    """Polls MongoDB for pending reminders that are due and broadcasts them via WebSocket."""
    try:
        collection = get_collection("reminders")
        now = datetime.now(timezone.utc)

        # Find pending reminders where execute_at <= now
        cursor = collection.find({
            "status": "pending",
            "execute_at": {"$lte": now}
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


async def self_ping():
    """
    Pings the /health endpoint of this very Space every 4 minutes.
    This generates real inbound HTTP traffic so HuggingFace does NOT
    mark the container as idle and shut it down.

    Requires the SPACE_HOST env var to be set in HuggingFace Space secrets,
    e.g.  SPACE_HOST=https://lagnam-jarvis-agents.hf.space
    """
    if not _SELF_URL:
        logger.debug("[self-ping] SPACE_HOST not set — skipping self-ping.")
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{_SELF_URL}/health")
        logger.info("[self-ping] %s/health -> %s", _SELF_URL, r.status_code)
    except Exception as exc:
        logger.warning("[self-ping] Failed: %s", exc)


def start_scheduler():
    if not scheduler.running:
        # Poll reminders every 10 seconds
        scheduler.add_job(check_reminders, 'interval', seconds=10)
        # Self-ping every 4 minutes to prevent HuggingFace idle shutdown
        scheduler.add_job(self_ping, 'interval', minutes=4, id='self_ping')
        scheduler.start()
        logger.info("[scheduler] Started reminder polling + self-ping scheduler.")

from datetime import UTC, datetime, timedelta
from app.core.mongodb import get_collection

class ConversationStateService:
    def __init__(self):
        self.collection = get_collection("conversation_state")

    async def set_pending_action(self, user_id: str, action_data: dict):
        """Saves a pending action (like a clarification request) for a user."""
        await self.collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "pending_action": action_data,
                    "created_at": datetime.now(UTC)
                }
            },
            upsert=True
        )

    async def get_pending_action(self, user_id: str) -> dict:
        """Retrieves and then DELETES the pending action for a user (one-time use)."""
        doc = await self.collection.find_one_and_delete({"user_id": user_id})
        if doc and doc.get("created_at"):
            # Expire state after 5 minutes
            if datetime.now(UTC) - doc["created_at"].replace(tzinfo=UTC) > timedelta(minutes=5):
                return None
            return doc.get("pending_action")
        return None

conversation_state = ConversationStateService()

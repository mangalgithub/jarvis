from datetime import UTC, datetime

from app.core.mongodb import get_collection
from app.tools.memory_tools import parse_memory_command
from app.core.embeddings import embedder

CATEGORY_EMOJI = {
    "personal": "👤",
    "diet": "🥗",
    "finance": "💰",
    "health": "🏋️",
    "preferences": "⚙️",
    "goals": "🎯",
    "work": "💼",
    "other": "📝",
}


class MemoryAgent:
    name = "memory"

    async def run(self, context: dict) -> dict:
        message = context.get("message", "")
        user_id = context.get("user_id", "default-user")
        command = await parse_memory_command(message)
        operation = command["operation"]

        try:
            if operation == "save_memory":
                return await self._save(user_id, command)
            if operation == "recall_memory":
                return await self._recall(user_id, command)
            if operation == "delete_memory":
                return await self._delete(user_id, command)
            if operation == "clear_memories":
                return await self._clear(user_id)
            return await self._list(user_id)
        except Exception as error:
            return {
                "reply": "Memory operation failed. Check MongoDB is running.",
                "actions": [{"type": "memory_operation_failed", "error": str(error)}],
            }

    # ── Save ───────────────────────────────────────────────────────────────

    async def _save(self, user_id: str, command: dict) -> dict:
        key = command["key"]
        value = command["value"]
        category = command["category"]

        if not key or not value:
            return {
                "reply": (
                    "I couldn't understand what to remember. "
                    "Try: 'Remember I am vegetarian' or 'My monthly salary is ₹50,000'."
                ),
                "actions": [{"type": "memory_parse_empty"}],
            }

        now = datetime.now(UTC)
        embedding = embedder.get_embedding(f"{key}: {value}")
        
        await get_collection("user_memory").update_one(
            {"user_id": user_id, "key": key},
            {
                "$set": {
                    "value": value, 
                    "category": category, 
                    "embedding": embedding,
                    "updated_at": now
                },
                "$setOnInsert": {"user_id": user_id, "key": key, "created_at": now},
            },
            upsert=True,
        )
        emoji = CATEGORY_EMOJI.get(category, "📝")
        return {
            "reply": f"Got it! {emoji} I'll remember: **{key.replace('_', ' ')}** → {value}",
            "actions": [{"type": "memory_saved", "key": key, "value": value, "category": category}],
        }

    # ── Recall ─────────────────────────────────────────────────────────────

    async def _recall(self, user_id: str, command: dict) -> dict:
        query = command.get("query") or command.get("key")
        if not query:
            return await self._list(user_id)
        doc = await get_collection("user_memory").find_one(
            {"user_id": user_id, "key": {"$regex": query, "$options": "i"}}
        )
        if not doc:
            return {
                "reply": f"I don't have anything stored about '{query}'.",
                "actions": [{"type": "memory_not_found", "query": query}],
            }
        return {
            "reply": f"Here's what I know about **{doc['key'].replace('_', ' ')}**: {doc['value']}",
            "actions": [{"type": "memory_recalled", "key": doc["key"], "value": doc["value"]}],
        }

    # ── Delete ─────────────────────────────────────────────────────────────

    async def _delete(self, user_id: str, command: dict) -> dict:
        query = command.get("query") or command.get("key")
        if not query:
            return {"reply": "Tell me what to forget, e.g. 'Forget my diet preference'.", "actions": []}
        result = await get_collection("user_memory").delete_one(
            {"user_id": user_id, "key": {"$regex": query, "$options": "i"}}
        )
        if result.deleted_count == 0:
            return {"reply": f"I don't have anything stored about '{query}'.", "actions": []}
        return {
            "reply": f"Done — I've forgotten your **{query.replace('_', ' ')}**.",
            "actions": [{"type": "memory_deleted", "key": query}],
        }

    # ── Clear ──────────────────────────────────────────────────────────────

    async def _clear(self, user_id: str) -> dict:
        result = await get_collection("user_memory").delete_many({"user_id": user_id})
        return {
            "reply": f"Cleared! I've forgotten all {result.deleted_count} things I knew about you.",
            "actions": [{"type": "memories_cleared", "count": result.deleted_count}],
        }

    # ── List ───────────────────────────────────────────────────────────────

    async def _list(self, user_id: str) -> dict:
        docs = await get_collection("user_memory").find(
            {"user_id": user_id}
        ).sort("category", 1).to_list(length=100)

        if not docs:
            return {
                "reply": (
                    "I don't know anything about you yet! "
                    "Try: 'Remember I am vegetarian' or 'My monthly salary is ₹50,000'."
                ),
                "actions": [{"type": "memories_empty"}],
            }

        groups: dict[str, list] = {}
        for doc in docs:
            cat = doc.get("category", "other")
            groups.setdefault(cat, []).append(doc)

        lines = []
        for cat, items in groups.items():
            emoji = CATEGORY_EMOJI.get(cat, "📝")
            lines.append(f"\n{emoji} **{cat.title()}**")
            for item in items:
                lines.append(f"  • {item['key'].replace('_', ' ')}: {item['value']}")

        serialized = [
            {"key": d["key"], "value": d["value"], "category": d.get("category", "other")}
            for d in docs
        ]
        return {
            "reply": f"Here's what I know about you ({len(docs)} facts):" + "\n".join(lines),
            "actions": [{"type": "memories_listed", "count": len(docs), "memories": serialized}],
        }

    # ── Context injection helper ───────────────────────────────────────────

    async def get_context_string(self, user_id: str, current_message: str = "") -> str:
        """
        Retrieves relevant user facts using Semantic Search (RAG).
        If current_message is provided, it finds the most contextually related facts.
        """
        docs = await get_collection("user_memory").find({"user_id": user_id}).to_list(length=100)
        if not docs:
            return ""

        # If no message provided, just return everything (legacy behavior)
        if not current_message:
            facts = [f"{d['key'].replace('_', ' ')}: {d['value']}" for d in docs]
            return "User profile — " + " | ".join(facts)

        # Perform Semantic Search
        query_vec = embedder.get_embedding(current_message)
        scored_docs = []
        
        for doc in docs:
            embedding = doc.get("embedding")
            if embedding:
                score = embedder.cosine_similarity(query_vec, embedding)
                scored_docs.append((score, doc))
            else:
                # Fallback for old docs without embeddings
                scored_docs.append((0.1, doc))

        # Sort by similarity score and take top 5
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        top_facts = [
            f"{d['key'].replace('_', ' ')}: {d['value']}" 
            for score, d in scored_docs[:5] 
            if score > 0.25 # Lowered threshold to catch more context
        ]

        if not top_facts:
            return ""

        return "Relevant user context — " + " | ".join(top_facts)

    # ── Dashboard helper ───────────────────────────────────────────────────

    async def get_dashboard_memory(self, user_id: str) -> dict:
        docs = await get_collection("user_memory").find(
            {"user_id": user_id}
        ).sort("category", 1).to_list(length=100)

        groups: dict[str, list] = {}
        for doc in docs:
            cat = doc.get("category", "other")
            groups.setdefault(cat, []).append({"key": doc["key"], "value": doc["value"]})

        return {"total": len(docs), "categories": groups}

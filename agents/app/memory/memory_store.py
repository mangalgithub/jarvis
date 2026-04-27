class MemoryStore:
    async def get_user_memory(self, user_id: str):
        return {}

    async def save_user_memory(self, user_id: str, key: str, value):
        return {"user_id": user_id, "key": key, "value": value}

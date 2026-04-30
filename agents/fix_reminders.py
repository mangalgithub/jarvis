import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_reminders():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["jarvis"]
    collection = db["reminders"]
    
    cursor = collection.find({"status": "pending"})
    async for doc in cursor:
        execute_at = doc.get("execute_at")
        if execute_at:
            try:
                dt = datetime.fromisoformat(execute_at)
                if dt.tzinfo is not None:
                    utc_dt = dt.astimezone(timezone.utc).isoformat()
                    await collection.update_one({"_id": doc["_id"]}, {"$set": {"execute_at": utc_dt}})
                    print(f"Updated {doc['_id']} from {execute_at} to {utc_dt}")
            except Exception as e:
                print(f"Error parsing {execute_at}: {e}")

if __name__ == "__main__":
    asyncio.run(fix_reminders())

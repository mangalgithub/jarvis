class HealthAgent:
    name = "health"

    async def run(self, context):
        return {"summary": "Health agent is ready."}

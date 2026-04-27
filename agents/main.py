from fastapi import FastAPI

from app.api.routes.chat import router as chat_router

app = FastAPI(title="Jarvis Agent Service")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "jarvis-agents"}


app.include_router(chat_router, prefix="/agent", tags=["agent"])

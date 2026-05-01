from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.websockets import router as websockets_router
from app.core.scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield

app = FastAPI(title="Jarvis Agent Service", lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "jarvis-agents"}


app.include_router(auth_router, prefix="/agent/auth", tags=["auth"])
app.include_router(chat_router, prefix="/agent", tags=["chat"])
app.include_router(dashboard_router, prefix="/agent", tags=["dashboard"])
app.include_router(websockets_router, prefix="/api", tags=["websockets"])

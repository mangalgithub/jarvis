from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.websockets import router as websockets_router
from app.core.scheduler import start_scheduler

from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield

app = FastAPI(title="Jarvis Agent Service", lifespan=lifespan)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://jarvis-personal-os.vercel.app", # Placeholder for your Vercel URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For initial deployment ease, allow all. Refine later for security.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "jarvis-agents"}


app.include_router(auth_router, prefix="/agent/auth", tags=["auth"])
app.include_router(chat_router, prefix="/agent", tags=["chat"])
app.include_router(dashboard_router, prefix="/agent", tags=["dashboard"])
app.include_router(websockets_router, prefix="/api", tags=["websockets"])

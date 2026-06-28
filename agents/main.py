from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.websockets import router as websockets_router
from app.core.scheduler import start_scheduler
from app.core.mongodb import get_collection

from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    
    # Add MongoDB indexes for query performance
    await get_collection("nutrition_logs").create_index([("user_id", 1), ("logged_at", -1)])
    await get_collection("water_logs").create_index([("user_id", 1), ("logged_at", -1)])
    await get_collection("expenses").create_index([("user_id", 1), ("created_at", -1)])
    
    yield

import logfire

app = FastAPI(title="Jarvis Agent Service", lifespan=lifespan)

# Configure Logfire (send_to_logfire='if-token-present' ensures it doesn't crash if unauthenticated locally)
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_fastapi(app)
# Instrument standard logging
logfire.instrument_pydantic()

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


from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.guardrails import check_rate_limit
import jwt
from app.core.config import settings

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if not (path.startswith("/agent/chat") or path.startswith("/agent/dashboard")):
        return await call_next(request)

    identity = request.client.host if request.client else "unknown"
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            identity = payload.get("sub", identity)
        except Exception:
            pass

    limit = 10 if path.startswith("/agent/chat") else 30
    
    allowed = await check_rate_limit(path, identity, limit, window=60)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please try again later."}
        )

    return await call_next(request)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "jarvis-agents"}


app.include_router(auth_router, prefix="/agent/auth", tags=["auth"])
app.include_router(chat_router, prefix="/agent", tags=["chat"])
app.include_router(dashboard_router, prefix="/agent", tags=["dashboard"])
app.include_router(websockets_router, prefix="/api", tags=["websockets"])

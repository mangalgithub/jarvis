from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.websockets import router as websockets_router
from app.core.scheduler import start_scheduler
from app.core.mongodb import get_collection

from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


async def create_mongodb_indexes():
    """Create indexes for the app's real query patterns."""
    index_specs = [
        ("users", [("email", 1)], {"unique": True, "name": "uniq_users_email"}),

        ("expenses", [("user_id", 1), ("created_at", -1)], {"name": "idx_expenses_user_created"}),
        ("expenses", [("user_id", 1), ("occurred_at", -1)], {"name": "idx_expenses_user_occurred"}),
        ("expenses", [("user_id", 1), ("category", 1), ("occurred_at", -1)], {"name": "idx_expenses_user_category_occurred"}),

        ("income", [("user_id", 1), ("occurred_at", -1)], {"name": "idx_income_user_occurred"}),
        ("budgets", [("user_id", 1), ("category", 1), ("period", 1)], {"unique": True, "name": "uniq_budgets_user_category_period"}),
        ("recurring_expenses", [("user_id", 1), ("created_at", -1)], {"name": "idx_recurring_user_created"}),
        ("savings_goals", [("user_id", 1), ("created_at", -1)], {"name": "idx_savings_user_created"}),

        ("nutrition_logs", [("user_id", 1), ("logged_at", -1)], {"name": "idx_nutrition_user_logged"}),
        ("water_logs", [("user_id", 1), ("logged_at", -1)], {"name": "idx_water_user_logged"}),
        ("workout_logs", [("user_id", 1), ("logged_at", -1)], {"name": "idx_workout_user_logged"}),
        ("health_goals", [("user_id", 1)], {"unique": True, "name": "uniq_health_goals_user"}),
        ("nutrition_knowledge", [("food_name", 1)], {"unique": True, "name": "uniq_nutrition_food_name"}),

        ("user_memory", [("user_id", 1), ("key", 1)], {"unique": True, "name": "uniq_memory_user_key"}),
        ("user_memory", [("user_id", 1), ("category", 1)], {"name": "idx_memory_user_category"}),

        ("pending_actions", [("user_id", 1), ("agent", 1), ("created_at", -1)], {"name": "idx_pending_user_agent_created"}),

        ("reminders", [("status", 1), ("execute_at", 1)], {"name": "idx_reminders_status_execute_at"}),
        ("reminders", [("user_id", 1), ("status", 1), ("execute_at", 1)], {"name": "idx_reminders_user_status_execute_at"}),
    ]

    for collection_name, keys, options in index_specs:
        collection = get_collection(collection_name)
        index_name = options.get("name")

        try:
            existing_indexes = await collection.index_information()

            # Check whether an index with the same key definition already exists
            existing_index_name = None

            for name, info in existing_indexes.items():
                if info.get("key") == keys:
                    existing_index_name = name
                    break

            if existing_index_name:
                if existing_index_name == index_name:
                    logger.info(
                        "MongoDB index %s already exists on %s",
                        index_name,
                        collection_name,
                    )
                else:
                    logger.info(
                        "MongoDB index already exists on %s as %s; "
                        "skipping creation of %s",
                        collection_name,
                        existing_index_name,
                        index_name,
                    )
                continue

            await collection.create_index(keys, **options)

            logger.info(
                "Created MongoDB index %s on %s",
                index_name,
                collection_name,
            )

        except Exception as exc:
            logger.warning(
                "Could not create MongoDB index %s on %s: %s",
                index_name or keys,
                collection_name,
                exc,
            )

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    await create_mongodb_indexes()
    
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

from fastapi import APIRouter, Depends

from app.core.auth import verify_token
from app.orchestrator.jarvis_orchestrator import run_orchestrator
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user_id: str = Depends(verify_token)):
    request.user_id = user_id  # Security override
    return await run_orchestrator(request)

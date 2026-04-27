from fastapi import APIRouter

from app.orchestrator.jarvis_orchestrator import run_orchestrator
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return await run_orchestrator(request)

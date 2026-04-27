from app.schemas.chat import ChatRequest, ChatResponse


async def run_orchestrator(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        reply=f"Jarvis received your request: {request.message}",
        actions=[
            {
                "type": "message_received",
                "user_id": request.user_id,
            }
        ],
    )

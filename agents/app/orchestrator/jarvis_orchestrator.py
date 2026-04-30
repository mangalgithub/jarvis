import json
import re

from app.agents.finance_agent import FinanceAgent
from app.agents.news_agent import NewsAgent
from app.core.llm import LLMUnavailableError, generate_response
from app.schemas.chat import ChatRequest, ChatResponse

finance_agent = FinanceAgent()
news_agent = NewsAgent()

VALID_INTENTS = {
    "expense_tracking",
    "health_tracking",
    "news_summary",
    "stock_analysis",
    "learning_help",
    "general_chat",
}


def parse_intents_from_llm_response(response_text: str) -> list[str]:
    match = re.search(r"\{.*\}", response_text, flags=re.DOTALL)
    if not match:
        return []

    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []

    raw_intents = payload.get("intents", [])
    if not isinstance(raw_intents, list):
        return []

    intents = [
        intent
        for intent in raw_intents
        if isinstance(intent, str) and intent in VALID_INTENTS
    ]

    if "general_chat" in intents and len(intents) > 1:
        intents = [intent for intent in intents if intent != "general_chat"]

    return intents or ["general_chat"]


async def detect_intents(message: str) -> tuple[list[str], str]:
    prompt = f"""
Classify the user's message into one or more Jarvis intents.

Allowed intents:
- expense_tracking: personal finance, expenses, income, budgets, savings goals, recurring payments, spending analytics
- health_tracking: water, workout, protein, calories, gym, or health tracking
- news_summary: news, headlines, India/world/current events summaries
- stock_analysis: stocks, market, mutual funds, Nifty, Sensex, investments
- learning_help: learning plans, courses, YouTube, AI/tech study help
- general_chat: anything else

Return only valid JSON in this exact shape:
{{"intents":["expense_tracking"]}}

User message: {message}
"""

    response_text = await generate_response(
        prompt,
        system_prompt=(
            "You are an intent classifier for Jarvis. "
            "Return strict JSON only, with no markdown or commentary."
        ),
        temperature=0,
    )
    intents = parse_intents_from_llm_response(response_text)

    if not intents:
        raise LLMUnavailableError(
            f"LLM returned an invalid intent payload: {response_text}"
        )

    return intents, "llm"


async def run_orchestrator(request: ChatRequest) -> ChatResponse:
    direct_finance_action = re.search(
        r"\b(?:delete|update)\s+expense\s+id\s+[a-fA-F0-9]{24}\b",
        request.message,
    )

    if direct_finance_action or finance_agent.is_confirmation_reply(request.message):
        try:
            if direct_finance_action or await finance_agent.has_pending_confirmation(request.user_id):
                result = await finance_agent.run(
                    {
                        "user_id": request.user_id,
                        "message": request.message,
                        "intents": ["expense_tracking"],
                    }
                )
                return ChatResponse(
                    reply=result["reply"],
                    actions=[
                        {
                            "type": "intent_detected",
                            "intents": ["expense_tracking"],
                            "source": "direct_finance_action"
                            if direct_finance_action
                            else "pending_confirmation",
                        },
                        *result["actions"],
                    ],
                )
        except Exception as error:
            return ChatResponse(
                reply="I could not process the pending confirmation.",
                actions=[
                    {
                        "type": "confirmation_processing_failed",
                        "error": str(error),
                    }
                ],
            )

    try:
        intents, intent_source = await detect_intents(request.message)
    except LLMUnavailableError as error:
        return ChatResponse(
            reply=(
                "I could not detect the intent because the LLM is unavailable. "
                "Please check your Groq API key and try again."
            ),
            actions=[
                {
                    "type": "intent_detection_failed",
                    "source": "llm",
                    "error": str(error),
                }
            ],
        )

    context = {
        "user_id": request.user_id,
        "message": request.message,
        "intents": intents,
    }

    if "expense_tracking" in intents:
        result = await finance_agent.run(context)
        return ChatResponse(
            reply=result["reply"],
            actions=[
                {
                    "type": "intent_detected",
                    "intents": intents,
                    "source": intent_source,
                },
                *result["actions"],
            ],
        )

    if "news_summary" in intents:
        result = await news_agent.run(context)
        return ChatResponse(
            reply=result["reply"],
            actions=[
                {
                    "type": "intent_detected",
                    "intents": intents,
                    "source": intent_source,
                },
                *result["actions"],
            ],
        )

    return ChatResponse(
        reply=(
            "I can hear you. Finance and news tracking are active; health, "
            "learning, and stock agents are the next modules to wire in."
        ),
        actions=[
            {
                "type": "intent_detected",
                "user_id": request.user_id,
                "intents": intents,
                "source": intent_source,
            }
        ],
    )

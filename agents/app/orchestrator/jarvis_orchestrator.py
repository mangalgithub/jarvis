import json
import re

from app.agents.finance_agent import FinanceAgent
from app.agents.health_agent import HealthAgent
from app.agents.news_agent import NewsAgent
from app.core.llm import LLMUnavailableError, generate_response
from app.schemas.chat import ChatRequest, ChatResponse

finance_agent = FinanceAgent()
news_agent = NewsAgent()
health_agent = HealthAgent()

VALID_INTENTS = {
    "expense_tracking",
    "health_tracking",
    "news_summary",
    "stock_analysis",
    "learning_help",
    "general_chat",
}

# Pre-LLM keyword shortcuts — catches obvious messages without a Groq round-trip
# These cover the most common health phrases the LLM tends to miss.
_HEALTH_RE = re.compile(
    r"\b(?:"
    # Water
    r"dran?k?|drink(?:ing)?|glass(?:es)?|water|hydrat"
    # Workouts
    r"|workout|gym|ran|run(?:ning)?|jog(?:ged)?|walk(?:ed|ing)?"
    r"|exercise|training|cardio|yoga|swim(?:ming)?"
    # Food actions
    r"|eat(?:ing|s)?|ate|eaten|had|having|consumed"
    # Food types — Indian
    r"|pizza|burger|biryani|rice|roti|chapati|dosa|idli|dal|sabzi"
    r"|paneer|chicken|mutton|egg|paratha|naan|rajma|chole"
    # Food types — Western / common
    r"|sandwich|pasta|noodles|salad|bread|soup|sushi|steak|oats"
    r"|apple|banana|mango|fruit|juice|milk|curd|yogurt|cheese"
    # Explicit nutrition
    r"|calori(?:e|es)|protein|carbs|nutrition|meal|lunch|dinner|breakfast|snack"
    # Health / fitness general
    r"|health|fitness|weight|bmi|steps|sleep"
    r")\b",
    re.IGNORECASE,
)

# Finance keywords that should override health even if health words appear
_FINANCE_KEYWORDS = {
    "expense", "spent", "spend", "budget", "income",
    "salary", "transaction", "payment", "saving",
}

_NEWS_RE = re.compile(
    r"\b(?:news|headline|briefing|latest|today'?s?\s+news)\b",
    re.IGNORECASE,
)


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

    # ── Pre-LLM keyword shortcuts (faster + more reliable for simple messages) ──
    msg_lower = request.message.lower()
    is_finance = any(kw in msg_lower for kw in _FINANCE_KEYWORDS)

    if _HEALTH_RE.search(request.message) and not is_finance:
        intents, intent_source = ["health_tracking"], "regex_shortcut"
    elif _NEWS_RE.search(request.message) and not is_finance:
        intents, intent_source = ["news_summary"], "regex_shortcut"
    else:
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
                {"type": "intent_detected", "intents": intents, "source": intent_source},
                *result["actions"],
            ],
        )

    if "health_tracking" in intents:
        result = await health_agent.run(context)
        return ChatResponse(
            reply=result["reply"],
            actions=[
                {"type": "intent_detected", "intents": intents, "source": intent_source},
                *result["actions"],
            ],
        )

    return ChatResponse(
        reply=(
            "I can hear you. Finance, news, and health tracking are active; "
            "stock, learning, and memory agents are next."
        ),
        actions=[{"type": "intent_detected", "user_id": request.user_id, "intents": intents, "source": intent_source}],
    )

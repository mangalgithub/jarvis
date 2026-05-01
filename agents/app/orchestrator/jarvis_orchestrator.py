import asyncio
import json
import re

from app.agents.finance_agent import FinanceAgent
from app.agents.health_agent import HealthAgent
from app.agents.news_agent import NewsAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.stock_agent import StockAgent
from app.agents.learning_agent import LearningAgent
from app.agents.reminder_agent import ReminderAgent
from app.core.llm import LLMUnavailableError, generate_response
from app.schemas.chat import ChatRequest, ChatResponse

finance_agent = FinanceAgent()
news_agent = NewsAgent()
health_agent = HealthAgent()
memory_agent = MemoryAgent()
stock_agent = StockAgent()
learning_agent = LearningAgent()
reminder_agent = ReminderAgent()

VALID_INTENTS = {
    "expense_tracking",
    "health_tracking",
    "news_summary",
    "stock_analysis",
    "learning_help",
    "memory_management",
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

_MEMORY_RE = re.compile(
    r"\b(?:remember|forget|what do you know|my profile|memory)\b"
    r"|^my \w+ is\b"
    r"|^i (?:go to|always|usually)\b",
    re.IGNORECASE,
)

_STOCK_RE = re.compile(
    r"\b(?:"
    r"stock|share|nifty|sensex|bank nifty|market|equity"
    r"|mutual fund|mf\b|nav|sip|folio"
    r"|reliance|tcs|infosys|wipro|hdfc|icici|sbi|bajaj|titan"
    r"|midcap|smallcap|large.?cap|index|gainers|losers|top stocks"
    r"|ipo|dividends?|returns?|portfolio"
    r")\b",
    re.IGNORECASE,
)

_LEARNING_RE = re.compile(
    r"\b(?:"
    r"learn(?:ing)?|teach me|tutorial|course|roadmap|study"
    r"|how to (?:become|code|program|build|master|start learning)"
    r"|youtube|video|playlist|lecture|syllabus"
    r"|python|javascript|java|react|machine learning|deep learning"
    r"|data science|devops|system design|dsa|algorithms|sql"
    r")\b",
    re.IGNORECASE,
)

_REMINDER_RE = re.compile(
    r"\b(?:remind(?:er)?|timer|set a timer|schedule|alert me|ping me|acknowledge reminder)\b",
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
- memory_management: saving/recalling personal facts, user preferences, erasing memory
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

    # Memory gets absolute priority if it matches a clear memory pattern
    if _MEMORY_RE.search(request.message):
        intents, intent_source = ["memory_management"], "regex_shortcut"
    elif _REMINDER_RE.search(request.message) and not is_finance:
        intents, intent_source = ["reminder_management"], "regex_shortcut"
    elif _STOCK_RE.search(request.message) and not is_finance:
        intents, intent_source = ["stock_analysis"], "regex_shortcut"
    elif _LEARNING_RE.search(request.message) and not is_finance:
        intents, intent_source = ["learning_help"], "regex_shortcut"
    elif _HEALTH_RE.search(request.message) and not is_finance:
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

    user_memory = await memory_agent.get_context_string(request.user_id, request.message)

    context = {
        "user_id": request.user_id,
        "message": request.message,
        "intents": intents,
        "user_memory": user_memory,
    }

    agent_map = {
        "expense_tracking": finance_agent,
        "news_summary": news_agent,
        "health_tracking": health_agent,
        "memory_management": memory_agent,
        "stock_analysis": stock_agent,
        "learning_help": learning_agent,
        "reminder_management": reminder_agent,
    }

    executed_agents = []
    for intent in intents:
        if intent in agent_map and agent_map[intent] not in executed_agents:
            executed_agents.append(agent_map[intent])

    if not executed_agents:
        return ChatResponse(
            reply=(
                "I can hear you. Finance, news, health, memory, stock, learning, and reminder agents are all active!"
            ),
            actions=[{"type": "intent_detected", "user_id": request.user_id, "intents": intents, "source": intent_source}],
        )

    # Run all mapped agents concurrently
    results = await asyncio.gather(*(agent.run(context) for agent in executed_agents), return_exceptions=True)

    combined_reply = []
    combined_actions = [{"type": "intent_detected", "intents": intents, "source": intent_source}]

    for i, res in enumerate(results):
        agent_name = executed_agents[i].name
        if isinstance(res, Exception):
            combined_reply.append(f"⚠️ **{agent_name.title()} Agent encountered an error:** {res}")
            combined_actions.append({"type": f"{agent_name}_error", "error": str(res)})
        else:
            if res.get("reply"):
                combined_reply.append(res["reply"])
            if res.get("actions"):
                combined_actions.extend(res["actions"])

    return ChatResponse(
        reply="\n\n".join(combined_reply),
        actions=combined_actions,
    )

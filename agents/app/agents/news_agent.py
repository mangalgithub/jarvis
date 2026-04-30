import re

from app.core.llm import LLMUnavailableError, generate_response
from app.core.mongodb import get_collection
from app.tools.news_tools import (
    NewsAPIError,
    detect_news_category,
    fetch_multi_category_news,
    fetch_news,
)

# Maps intent keywords to newsapi categories
CATEGORY_DISPLAY = {
    "india": "India",
    "world": "World",
    "technology": "Technology",
    "ai": "AI & Tech",
    "business": "Business",
    "sports": "Sports",
    "science": "Science",
}

# How many headline lines to show in the chat reply
HEADLINE_LIMIT = 5


def _format_articles_reply(category: str, articles: list[dict]) -> str:
    """Format articles into a short readable text reply."""
    label = CATEGORY_DISPLAY.get(category, category.title())
    if not articles:
        return f"I could not find any {label} news right now."

    lines = []
    for i, article in enumerate(articles[:HEADLINE_LIMIT], start=1):
        title = article["title"].strip().rstrip(".")
        source = article["source"]
        lines.append(f"{i}. {title}" + (f" ({source})" if source else ""))

    return f"Here are the latest {label} headlines:\n" + "\n".join(lines)


def _detect_query_type(message: str) -> tuple[str, list[str]]:
    """
    Returns (query_type, [categories]).
    query_type: 'summary' | 'briefing' | 'search'
    """
    normalized = message.lower()

    # "morning briefing" or "daily briefing" → fetch india + world + ai
    if re.search(r"\b(morning|daily|evening)\s*briefing\b", normalized):
        return "briefing", ["india", "world", "ai"]

    # "latest news" with no specific topic → india by default
    if re.search(r"\b(latest|today'?s?|current|top)\s*(news|headlines)\b", normalized) and not any(
        word in normalized
        for word in ["ai", "tech", "business", "sports", "science", "world", "international"]
    ):
        return "summary", ["india"]

    # "summarize" → use LLM to summarize fetched articles
    if re.search(r"\bsummar(y|ize|ise)\b", normalized):
        return "summary", [detect_news_category(message)]

    return "summary", [detect_news_category(message)]


async def _llm_summarize(articles: list[dict], category: str) -> str:
    """Use the Groq LLM to produce a 3-4 sentence summary of the top articles."""
    titles_block = "\n".join(
        f"- {a['title']}" + (f": {a['description']}" if a.get("description") else "")
        for a in articles[:8]
    )
    label = CATEGORY_DISPLAY.get(category, category.title())
    prompt = f"""
You are Jarvis, a concise personal news assistant.

Based on these {label} news headlines and descriptions, write a short 3-4 sentence narrative summary covering the most important stories. Be factual and concise.

Headlines:
{titles_block}

Summary:
"""
    try:
        summary = await generate_response(
            prompt,
            system_prompt="You are Jarvis, a concise personal news assistant. Summarize news in 3-4 sentences.",
            temperature=0.3,
        )
        return summary.strip()
    except LLMUnavailableError:
        return _format_articles_reply(category, articles)


class NewsAgent:
    name = "news"

    async def run(self, context: dict) -> dict:
        message = context.get("message", "")
        user_id = context.get("user_id", "default-user")

        query_type, categories = _detect_query_type(message)

        # ----- Morning / Daily Briefing -----
        if query_type == "briefing" or len(categories) > 1:
            return await self._run_briefing(categories)

        # ----- Single category summary -----
        category = categories[0]
        return await self._run_single(message, category)

    async def _run_single(self, message: str, category: str) -> dict:
        try:
            articles = await fetch_news(category)
        except NewsAPIError as error:
            return {
                "reply": f"I could not fetch news right now: {error}",
                "actions": [{"type": "news_fetch_failed", "error": str(error)}],
            }

        # Decide whether to list headlines or give an LLM summary
        normalized = message.lower()
        use_summary = re.search(r"\bsummar(y|ize|ise)\b", normalized)

        if use_summary:
            reply = await _llm_summarize(articles, category)
        else:
            reply = _format_articles_reply(category, articles)

        return {
            "reply": reply,
            "actions": [
                {
                    "type": "news_fetched",
                    "category": category,
                    "article_count": len(articles),
                    "articles": articles[:10],
                }
            ],
        }

    async def _run_briefing(self, categories: list[str]) -> dict:
        results = await fetch_multi_category_news(categories)

        sections = []
        all_articles = {}

        for cat in categories:
            articles = results.get(cat, [])
            all_articles[cat] = articles
            label = CATEGORY_DISPLAY.get(cat, cat.title())
            if articles:
                headlines = "; ".join(a["title"].rstrip(".") for a in articles[:3])
                sections.append(f"**{label}**: {headlines}.")
            else:
                sections.append(f"**{label}**: No headlines available.")

        reply = "Good morning! Here's your daily briefing:\n\n" + "\n".join(sections)

        return {
            "reply": reply,
            "actions": [
                {
                    "type": "news_briefing",
                    "categories": categories,
                    "articles": all_articles,
                }
            ],
        }

    async def get_dashboard_news(self, categories: list[str] | None = None) -> dict:
        """
        Called by the dashboard API to populate the news widget.
        Returns top headlines for each requested category.
        """
        if categories is None:
            categories = ["india", "world", "ai"]

        results = await fetch_multi_category_news(categories)
        output = {}
        for cat, articles in results.items():
            output[cat] = {
                "label": CATEGORY_DISPLAY.get(cat, cat.title()),
                "articles": articles[:5],
            }
        return output

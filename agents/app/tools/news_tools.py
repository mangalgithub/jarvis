import asyncio
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import settings
from app.core.mongodb import get_collection

# NewsAPI /v2/everything endpoint — works for all categories via q= param
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# Cache TTL per category (in minutes)
CACHE_TTL = {
    "india": 30,
    "world": 30,
    "technology": 60,
    "ai": 60,
    "business": 60,
    "sports": 30,
    "science": 120,
}

# Each category maps to a q= search string + optional extra params
# Using the /v2/everything endpoint as shown in the API docs:
# GET https://newsapi.org/v2/everything?q=bitcoin&apiKey=...
CATEGORY_PARAMS = {
    "india": {
        "q": "India OR Indian OR Delhi OR Mumbai OR Modi OR BJP OR Congress",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
    },
    "world": {
        "q": "world news OR international OR global OR United Nations OR geopolitics",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
    },
    "technology": {
        "q": "technology OR software OR startup OR gadget OR app OR cybersecurity",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
    },
    "ai": {
        "q": "artificial intelligence OR AI OR machine learning OR LLM OR OpenAI OR Gemini OR ChatGPT",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
    },
    "business": {
        "q": "business OR economy OR stock market OR finance OR GDP OR trade",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
    },
    "sports": {
        "q": "cricket OR IPL OR football OR sports OR tournament OR match OR Olympics",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
    },
    "science": {
        "q": "science OR space OR NASA OR research OR discovery OR climate OR quantum",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
    },
}

NEWS_CATEGORY_KEYWORDS = {
    "india": ["india", "indian", "delhi", "mumbai", "bangalore", "modi", "bjp", "congress"],
    "world": ["world", "international", "global", "us", "usa", "uk", "europe", "china", "russia"],
    "technology": ["technology", "tech", "software", "hardware", "gadget", "app", "startup"],
    "ai": ["ai", "artificial intelligence", "machine learning", "chatgpt", "llm", "openai", "gemini"],
    "business": ["business", "market", "economy", "stock", "finance", "startup", "company", "profit"],
    "sports": ["sports", "cricket", "football", "ipl", "match", "game", "player", "tournament"],
    "science": ["science", "space", "nasa", "research", "discovery", "climate"],
}


class NewsAPIError(Exception):
    pass


def detect_news_category(message: str) -> str:
    """Detect which news category the user is asking about."""
    normalized = message.lower()
    for category, keywords in NEWS_CATEGORY_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return category
    return "india"


async def _get_cached_news(category: str) -> list[dict] | None:
    """Return cached articles if they're still fresh, else None."""
    ttl_minutes = CACHE_TTL.get(category, 30)
    cutoff = datetime.now(UTC) - timedelta(minutes=ttl_minutes)
    doc = await get_collection("news_cache").find_one(
        {"category": category, "fetched_at": {"$gte": cutoff}}
    )
    return doc["articles"] if doc else None


async def _cache_news(category: str, articles: list[dict]) -> None:
    """Upsert articles into the cache collection."""
    await get_collection("news_cache").update_one(
        {"category": category},
        {
            "$set": {
                "articles": articles,
                "fetched_at": datetime.now(UTC),
                "category": category,
            }
        },
        upsert=True,
    )


def _normalize_article(raw: dict) -> dict:
    """Strip down a raw NewsAPI article to only what we need."""
    return {
        "title": raw.get("title") or "",
        "description": raw.get("description") or "",
        "url": raw.get("url") or "",
        "source": (raw.get("source") or {}).get("name") or "",
        "published_at": raw.get("publishedAt") or "",
        "image_url": raw.get("urlToImage") or "",
    }


def _is_junk_article(article: dict) -> bool:
    """Filter out removed/consent-wall/empty articles."""
    title = article.get("title") or ""
    url = article.get("url") or ""
    if not title or "[Removed]" in title:
        return True
    # Yahoo consent pages and similar paywalls
    if "consent.yahoo.com" in url:
        return True
    return False


async def fetch_news(category: str = "india", force_refresh: bool = False) -> list[dict]:
    """
    Fetch news articles for a category using the NewsAPI /v2/everything endpoint.
    Example: GET https://newsapi.org/v2/everything?q=India&apiKey=...
    Uses MongoDB cache to avoid hammering the API.
    Returns a list of normalized article dicts.
    """
    if not settings.news_api_key:
        raise NewsAPIError("NEWS_API_KEY is not configured")

    if not force_refresh:
        cached = await _get_cached_news(category)
        if cached is not None:
            return cached

    params = {
        **CATEGORY_PARAMS.get(category, CATEGORY_PARAMS["india"]),
        "apiKey": settings.news_api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(NEWSAPI_URL, params=params)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise NewsAPIError(f"NewsAPI request failed: {error}") from error

    data = response.json()

    if data.get("status") != "ok":
        raise NewsAPIError(f"NewsAPI error: {data.get('message', 'unknown error')}")

    raw_articles = data.get("articles") or []
    articles = [_normalize_article(raw) for raw in raw_articles]
    articles = [a for a in articles if not _is_junk_article(a)]

    await _cache_news(category, articles)
    return articles


async def fetch_multi_category_news(categories: list[str]) -> dict[str, list[dict]]:
    """Fetch multiple categories in parallel (best-effort, never raises)."""
    async def safe_fetch(cat: str) -> tuple[str, list[dict]]:
        try:
            articles = await fetch_news(cat)
            return cat, articles
        except NewsAPIError:
            return cat, []

    results = await asyncio.gather(*[safe_fetch(cat) for cat in categories])
    return dict(results)

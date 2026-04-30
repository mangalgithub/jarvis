import json
import re

import httpx

from app.core.config import settings
from app.core.llm import LLMUnavailableError, generate_response

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

LEARNING_OPERATIONS = {
    "search_videos",       # Search YouTube for topic
    "get_roadmap",         # Generate learning roadmap with LLM
    "get_playlist",        # Search for playlists on a topic
    "get_channel_videos",  # Get videos from a specific channel
    "recommend_courses",   # Recommend structured courses
}

LEARNING_TOPICS = {
    "python", "machine learning", "ai", "deep learning", "data science",
    "web development", "react", "javascript", "java", "c++", "rust",
    "system design", "dsa", "algorithms", "sql", "devops", "docker",
    "kubernetes", "cloud", "aws", "finance", "excel", "communication",
}


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def normalize_learning_command(payload: dict) -> dict:
    operation = payload.get("operation", "search_videos")
    if operation not in LEARNING_OPERATIONS:
        operation = "search_videos"
    return {
        "operation": operation,
        "topic": str(payload.get("topic") or "").strip(),
        "level": str(payload.get("level") or "beginner").strip().lower(),
        "duration": str(payload.get("duration") or "any").strip().lower(),
        "language": str(payload.get("language") or "english").strip().lower(),
        "channel": str(payload.get("channel") or "").strip(),
        "max_results": int(payload.get("max_results") or 5),
    }


async def parse_learning_command(message: str) -> dict:
    prompt = f"""Parse this learning/study request into strict JSON.

Allowed operations: {", ".join(sorted(LEARNING_OPERATIONS))}

JSON shape:
{{
  "operation": "search_videos",
  "topic": "machine learning",
  "level": "beginner",
  "duration": "any",
  "language": "english",
  "channel": "",
  "max_results": 5
}}

Rules:
- "learn python / tutorial on X / how to study X" → search_videos
- "roadmap for X / how to become X / plan to learn X" → get_roadmap
- "playlist for X / course series on X" → get_playlist
- "videos from Andrej Karpathy / channel X" → get_channel_videos
- "best courses for X / recommend me X" → recommend_courses
- level: beginner / intermediate / advanced (infer from message)
- duration: short (<10min), medium (10-30min), long (>30min), any
- language: english or hindi (detect from message)
- Return ONLY JSON. No markdown.

User message: {message}
"""
    try:
        response_text = await generate_response(
            prompt,
            system_prompt="You parse learning/study commands for Jarvis. Return strict JSON only.",
            temperature=0,
        )
        return normalize_learning_command(_parse_json(response_text))
    except LLMUnavailableError:
        # Regex fallback
        msg = message.lower()
        if "roadmap" in msg or "how to become" in msg:
            topic = re.sub(r"(roadmap|how to become|how to learn|plan for)\s*", "", msg).strip()
            return normalize_learning_command({"operation": "get_roadmap", "topic": topic})
        return normalize_learning_command({"operation": "search_videos", "topic": message})


# ── YouTube API helpers ────────────────────────────────────────────────────────

async def youtube_search(
    query: str,
    search_type: str = "video",
    max_results: int = 5,
    duration: str = "any",
) -> list[dict]:
    """Search YouTube using Data API v3."""
    api_key = settings.youtube_api_key
    if not api_key:
        return []

    params: dict = {
        "part": "snippet",
        "q": query,
        "type": search_type,
        "maxResults": max_results,
        "key": api_key,
        "relevanceLanguage": "en",
        "safeSearch": "moderate",
        "order": "relevance",
    }

    # Duration filter only applies to video searches
    if search_type == "video" and duration != "any":
        duration_map = {"short": "short", "medium": "medium", "long": "long"}
        params["videoDuration"] = duration_map.get(duration, "any")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{YOUTUBE_API_BASE}/search", params=params)
        resp.raise_for_status()
        data = resp.json()

    items = data.get("items", [])
    results = []
    for item in items:
        snippet = item.get("snippet", {})
        vid_id = item.get("id", {})
        if search_type == "video":
            video_id = vid_id.get("videoId")
            url = f"https://youtube.com/watch?v={video_id}" if video_id else ""
        elif search_type == "playlist":
            pl_id = vid_id.get("playlistId")
            url = f"https://youtube.com/playlist?list={pl_id}" if pl_id else ""
        elif search_type == "channel":
            ch_id = vid_id.get("channelId")
            url = f"https://youtube.com/channel/{ch_id}" if ch_id else ""
        else:
            url = ""

        results.append({
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "description": snippet.get("description", "")[:150],
            "published_at": snippet.get("publishedAt", "")[:10],
            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            "url": url,
        })
    return results


async def generate_roadmap(topic: str, level: str) -> str:
    """Use LLM to generate a structured learning roadmap."""
    prompt = f"""Create a concise, actionable learning roadmap for **{topic}** at {level} level.

Format:
📍 **Phase 1 — Foundations** (Week 1-2)
   • Topic 1
   • Topic 2

📍 **Phase 2 — Core Skills** (Week 3-4)
   • Topic 1
   • Topic 2

📍 **Phase 3 — Projects** (Week 5-6)
   • Build X
   • Practice Y

📍 **Resources**
   • Best free resource: ...
   • Best course: ...

Keep it under 300 words. Be specific and actionable."""

    try:
        return await generate_response(
            prompt,
            system_prompt="You are an expert learning coach. Create practical, structured roadmaps.",
            temperature=0.3,
        )
    except LLMUnavailableError:
        return f"Learning roadmap for {topic}: Search for beginner tutorials, then practice with projects."

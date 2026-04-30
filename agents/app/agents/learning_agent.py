import logging

from app.core.config import settings
from app.tools.learning_tools import (
    generate_roadmap,
    parse_learning_command,
    youtube_search,
)

logger = logging.getLogger(__name__)


class LearningAgent:
    name = "learning"

    async def run(self, context: dict) -> dict:
        message = context.get("message", "")
        command = await parse_learning_command(message)
        operation = command["operation"]

        if not settings.youtube_api_key:
            return {
                "reply": (
                    "YouTube API key is missing. "
                    "Add YOUTUBE_API_KEY to your agents/.env file."
                ),
                "actions": [{"type": "learning_no_api_key"}],
            }

        try:
            if operation == "get_roadmap":
                return await self._get_roadmap(command)
            if operation == "get_playlist":
                return await self._get_playlist(command)
            if operation == "get_channel_videos":
                return await self._get_channel_videos(command)
            if operation == "recommend_courses":
                return await self._recommend_courses(command)
            return await self._search_videos(command)
        except Exception as exc:
            logger.error("[LearningAgent] %s: %s", operation, exc, exc_info=True)
            return {
                "reply": f"Sorry, I couldn't fetch learning resources right now. ({exc})",
                "actions": [{"type": "learning_error", "error": str(exc)}],
            }

    # ── Search Videos ──────────────────────────────────────────────────────

    async def _search_videos(self, command: dict) -> dict:
        topic = command["topic"]
        level = command["level"]
        duration = command["duration"]
        language = command["language"]

        query = f"{topic} tutorial {level}"
        if language == "hindi":
            query += " in hindi"

        videos = await youtube_search(query, search_type="video", max_results=5, duration=duration)

        if not videos:
            return {
                "reply": f"No videos found for **{topic}**. Check your YouTube API key.",
                "actions": [{"type": "learning_no_results", "topic": topic}],
            }

        level_emoji = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(level, "🔵")
        reply_text = f"🎬 **{topic.title()} Videos** {level_emoji} {level.title()}"

        return {
            "reply": reply_text,
            "actions": [{"type": "learning_videos", "topic": topic, "level": level, "videos": videos}],
        }

    # ── Roadmap ────────────────────────────────────────────────────────────

    async def _get_roadmap(self, command: dict) -> dict:
        topic = command["topic"]
        level = command["level"]

        # Generate roadmap with LLM
        roadmap = await generate_roadmap(topic, level)

        # Also find 3 starter videos
        videos = await youtube_search(
            f"{topic} {level} tutorial complete",
            search_type="video",
            max_results=3,
        )

        return {
            "reply": roadmap,
            "actions": [
                {
                    "type": "learning_roadmap",
                    "topic": topic,
                    "level": level,
                    "roadmap": roadmap,
                    "starter_videos": videos,
                }
            ],
        }

    # ── Playlists ──────────────────────────────────────────────────────────

    async def _get_playlist(self, command: dict) -> dict:
        topic = command["topic"]
        level = command["level"]

        query = f"{topic} full course playlist {level}"
        playlists = await youtube_search(query, search_type="playlist", max_results=5)

        if not playlists:
            return {"reply": f"No playlists found for **{topic}**.", "actions": []}

        reply_text = f"📋 **{topic.title()} Playlists** ({level})"

        return {
            "reply": reply_text,
            "actions": [{"type": "learning_playlists", "topic": topic, "playlists": playlists}],
        }

    # ── Channel Videos ─────────────────────────────────────────────────────

    async def _get_channel_videos(self, command: dict) -> dict:
        channel = command["channel"] or command["topic"]
        topic = command["topic"]

        query = f"{channel} {topic}"
        videos = await youtube_search(query, search_type="video", max_results=5)

        if not videos:
            return {"reply": f"No videos found from **{channel}**.", "actions": []}

        reply_text = f"📺 **Videos by {channel}** on {topic}"

        return {
            "reply": reply_text,
            "actions": [{"type": "learning_channel", "channel": channel, "videos": videos}],
        }

    # ── Recommend Courses ──────────────────────────────────────────────────

    async def _recommend_courses(self, command: dict) -> dict:
        topic = command["topic"]
        level = command["level"]

        # Search for structured courses
        query = f"best {topic} course {level} 2024 2025 free"
        videos = await youtube_search(query, search_type="video", max_results=5, duration="long")
        playlists = await youtube_search(
            f"{topic} complete course {level}", search_type="playlist", max_results=3
        )

        reply_text = f"🎓 **Recommended {topic.title()} Courses** ({level})"

        return {
            "reply": reply_text,
            "actions": [
                {
                    "type": "learning_courses",
                    "topic": topic,
                    "level": level,
                    "playlists": playlists,
                    "videos": videos,
                }
            ],
        }

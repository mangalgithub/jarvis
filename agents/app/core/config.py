from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_FILE)


class Settings(BaseModel):
    app_name: str = "Jarvis Agent Service"
    mongodb_uri: str = getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_database: str = getenv("MONGODB_DATABASE", "jarvis")
    groq_api_key: str | None = getenv("GROQ_API_KEY")
    groq_model: str = getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    groq_api_url: str = getenv(
        "GROQ_API_URL",
        "https://api.groq.com/openai/v1/chat/completions",
    )
    google_api_key: str | None = getenv("GOOGLE_API_KEY") or getenv("GEMINI_API_KEY")
    news_api_key: str | None = getenv("NEWS_API_KEY")
    youtube_api_key: str | None = getenv("YOUTUBE_API_KEY")
    secret_key: str = getenv("SECRET_KEY", "super-secret-key-for-jarvis-os-32")
    access_token_expire_minutes: int = int(getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080")) # 7 days


settings = Settings()

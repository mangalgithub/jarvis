import httpx

from app.core.config import settings


class LLMUnavailableError(Exception):
    pass


async def generate_response(
    prompt: str,
    *,
    system_prompt: str = "You are Jarvis, a concise personal assistant.",
    temperature: float = 0,
) -> str:
    if not settings.groq_api_key:
        raise LLMUnavailableError("GROQ_API_KEY is not configured")

    payload = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                settings.groq_api_url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise LLMUnavailableError(str(error)) from error

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()

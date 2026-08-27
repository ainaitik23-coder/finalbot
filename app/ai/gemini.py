"""Gemini API wrapper (Google AI Studio, free tier)."""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type


class RateLimitError(Exception):
    """Raised when this specific key+model combo is rate-limited (HTTP 429)."""
    pass


def _gemini_url(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_not_exception_type(RateLimitError),
)
async def call_gemini(
    system_prompt: str, history: list[dict], user_message: str, api_key: str, model: str
) -> str:
    """
    history: list of {"role": "user"|"model", "text": "..."}
    Gemini uses "model" instead of "assistant" for its own turns.
    """
    contents = []
    for turn in history:
        contents.append({
            "role": "model" if turn["role"] == "assistant" else "user",
            "parts": [{"text": turn["content"]}],
        })
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 512,
        },
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            _gemini_url(model),
            params={"key": api_key},
            json=payload,
        )
        if resp.status_code == 429:
            raise RateLimitError(f"Gemini {model} rate-limited for key ...{api_key[-4:]}")
        resp.raise_for_status()
        data = resp.json()

    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

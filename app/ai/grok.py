"""Groq API wrapper (free tier, OpenAI-compatible chat completions)."""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type

from app.ai.gemini import RateLimitError

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_not_exception_type(RateLimitError),
)
async def call_groq(
    system_prompt: str, history: list[dict], user_message: str, api_key: str, model: str
) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.9,
        "max_tokens": 512,
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(GROQ_URL, json=payload, headers=headers)
        if resp.status_code == 429:
            raise RateLimitError(f"Groq {model} rate-limited for key ...{api_key[-4:]}")
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"].strip()

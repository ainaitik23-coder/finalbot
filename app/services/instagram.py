"""Sends replies back to Instagram via the Graph API."""
import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.utils.constants import GRAPH_API_BASE
from app.utils.helpers import truncate_reply

logger = logging.getLogger("instagram")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=6))
async def send_message(recipient_id: str, text: str) -> None:
    text = truncate_reply(text)
    url = f"{GRAPH_API_BASE}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    params = {"access_token": settings.IG_PAGE_ACCESS_TOKEN}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, params=params, json=payload)
        if resp.status_code >= 400:
            logger.error(f"Failed to send IG message: {resp.status_code} {resp.text}")
        resp.raise_for_status()


async def send_typing_indicator(recipient_id: str) -> None:
    """Optional: shows 'typing...' to the user while the AI generates a reply."""
    url = f"{GRAPH_API_BASE}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "sender_action": "typing_on",
    }
    params = {"access_token": settings.IG_PAGE_ACCESS_TOKEN}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(url, params=params, json=payload)
        except Exception as e:
            logger.warning(f"Typing indicator failed (non-critical): {e}")

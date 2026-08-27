"""
Tries keys in rotation order: all Gemini keys first, then all Groq keys
(order fixed by key_pool.py). On a 429 (rate limit) from a key, that key is
marked exhausted and the router immediately retries with the next key -
same conversation, same memory, just a different key/provider under the hood.

If every configured key across every provider is currently exhausted, raises
a RuntimeError tagged ALL_KEYS_EXHAUSTED, which app/ai/llm.py catches to send
the "kal baat karte hain" fallback message.
"""
import logging

from app.ai.gemini import call_gemini, RateLimitError
from app.ai.grok import call_groq
from app.ai.key_pool import key_pool
from app.utils.constants import PROVIDER_GEMINI, PROVIDER_GROQ

logger = logging.getLogger("router")

ALL_KEYS_EXHAUSTED = "ALL_KEYS_EXHAUSTED"

CALL_FNS = {
    PROVIDER_GEMINI: call_gemini,
    PROVIDER_GROQ: call_groq,
}
@router.get("/privacy")
async def privacy_policy():
    return {
        "policy": "Ye ek personal/testing chatbot hai jo Instagram DMs ka reply deta hai. "
                   "Koi user data third-party ke saath share nahi kiya jata. "
                   "Data sirf conversation ke liye store hota hai."
    }

async def generate_reply(system_prompt: str, history: list[dict], user_message: str) -> tuple[str, str]:
    """
    Returns (reply_text, provider_used).
    """
    total_slots = key_pool.slot_count()
    if total_slots == 0:
        raise RuntimeError("No API keys configured at all - check .env")

    last_error = None

    for _ in range(total_slots):
        slot = key_pool.next_slot()
        if slot is None:
            # every key is currently on cooldown
            raise RuntimeError(ALL_KEYS_EXHAUSTED)

        fn = CALL_FNS[slot.provider]
        try:
            reply = await fn(system_prompt, history, user_message, slot.key, slot.model)
            return reply, slot.provider
        except RateLimitError:
            key_pool.mark_exhausted(slot.provider, slot.key, slot.model)
            logger.info(
                f"{slot.provider}/{slot.model} key ...{slot.key[-4:]} rate-limited, rotating to next combo"
            )
            last_error = "rate_limited"
            continue
        except Exception as e:
            logger.warning(f"{slot.provider}/{slot.model} key ...{slot.key[-4:]} failed (non-rate-limit): {e}")
            last_error = e
            continue

    # tried every slot this round and none succeeded
    if key_pool.all_exhausted():
        raise RuntimeError(ALL_KEYS_EXHAUSTED)
    raise RuntimeError(f"All keys failed this round. Last error: {last_error}")

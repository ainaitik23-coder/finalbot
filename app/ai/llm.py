"""
Top-level interface the rest of the app calls into.
Keeps ai/router.py, ai/key_pool.py, ai/prompt.py etc as implementation details.
"""
import logging

from app.ai.prompt import build_system_prompt, get_fallback_message
from app.ai.router import generate_reply, ALL_KEYS_EXHAUSTED

logger = logging.getLogger("llm")

SYSTEM_PROMPT = build_system_prompt()

# Sent only when every configured key, across every provider, is rate-limited.
ALL_KEYS_EXHAUSTED_MESSAGE = "*kal baat karte hain ham aapse, abhi hamara thoda kaam chal raha hai*"


async def get_ai_reply(history: list[dict], user_message: str) -> tuple[str, str | None]:
    """
    history: [{"role": "user"|"assistant", "content": "..."}]
    Returns (reply_text, provider_used_or_none)
    Conversation history/memory is unaffected by which key or provider ends up
    generating the reply - that's decided purely inside router.py/key_pool.py.
    """
    try:
        reply, provider = await generate_reply(SYSTEM_PROMPT, history, user_message)
        return reply, provider
    except RuntimeError as e:
        if ALL_KEYS_EXHAUSTED in str(e):
            logger.warning("All API keys exhausted - sending out-of-capacity message")
            return ALL_KEYS_EXHAUSTED_MESSAGE, None
        logger.error(f"LLM generation failed: {e}")
        return get_fallback_message(), None
    except Exception as e:
        logger.error(f"Unexpected LLM error: {e}")
        return get_fallback_message(), None

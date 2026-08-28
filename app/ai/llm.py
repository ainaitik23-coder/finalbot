"""
Top-level interface the rest of the app calls into.
Keeps ai/router.py, ai/key_pool.py, ai/prompt.py etc as implementation details.
"""
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.ai.prompt import build_system_prompt, get_fallback_message
from app.ai.router import generate_reply, ALL_KEYS_EXHAUSTED

logger = logging.getLogger("llm")

IST = ZoneInfo("Asia/Kolkata")

BASE_PROMPT_PRIMARY = build_system_prompt(is_primary=True)
BASE_PROMPT_OTHERS = build_system_prompt(is_primary=False)

ALL_KEYS_EXHAUSTED_MESSAGE = "*kal baat karte hain ham aapse, abhi hamara thoda kaam chal raha hai*"

_THINK_BLOCK_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.IGNORECASE | re.DOTALL)
_THINK_UNCLOSED_RE = re.compile(r"<think(?:ing)?>.*$", re.IGNORECASE | re.DOTALL)


def _strip_reasoning(text: str) -> str:
    cleaned = _THINK_BLOCK_RE.sub("", text)
    cleaned = _THINK_UNCLOSED_RE.sub("", cleaned)
    return cleaned.strip()


def _current_time_context() -> str:
    now = datetime.now(IST)
    return (
        f"Abhi ka real time (India, IST): {now.strftime('%A, %d %B %Y, %I:%M %p')}. "
        f"Agar time/date/din puchha jaaye to yahi sahi jawab hai - kabhi guess ya galat time mat batana."
    )


async def get_ai_reply(
    history: list[dict], user_message: str, is_primary: bool = True
) -> tuple[str, str | None]:
    base_prompt = BASE_PROMPT_PRIMARY if is_primary else BASE_PROMPT_OTHERS
    system_prompt = f"{base_prompt}\n\n{_current_time_context()}"

    try:
        reply, provider = await generate_reply(system_prompt, history, user_message)
        reply = _strip_reasoning(reply)
        if not reply:
            logger.warning("Reply was empty after stripping reasoning tags - using fallback")
            return get_fallback_message(), provider
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

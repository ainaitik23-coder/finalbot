"""
Orchestrates a single incoming-message -> reply cycle:
load thread -> load history -> call LLM -> save both messages -> send reply.
"""
import logging

from app.ai.llm import get_ai_reply
from app.database.crud import get_or_create_thread, add_message, get_recent_messages
from app.database.database import get_session
from app.services.instagram import send_message, send_typing_indicator
from app.services.memory import messages_to_history

logger = logging.getLogger("conversation")


async def handle_incoming_message(sender_id: str, text: str) -> None:
    await send_typing_indicator(sender_id)

    async with get_session() as session:
        thread = await get_or_create_thread(session, sender_id)
        await add_message(session, thread.id, role="user", content=text)

        recent = await get_recent_messages(session, thread.id)
        history = messages_to_history(recent[:-1])  # exclude the message we just added

        reply_text, provider = await get_ai_reply(history, text)

        await add_message(session, thread.id, role="assistant", content=reply_text, provider=provider)

    try:
        await send_message(sender_id, reply_text)
    except Exception as e:
        logger.error(f"Failed to deliver reply to {sender_id}: {e}")

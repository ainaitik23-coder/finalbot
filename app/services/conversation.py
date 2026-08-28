"""
Orchestrates a single incoming-message -> reply cycle:
load thread -> load history -> call LLM -> save assistant message -> SCHEDULE
the actual send for later (see app/services/scheduler.py) instead of sending
immediately. A cron endpoint (/cron/process-scheduled) delivers it once its
scheduled time arrives - this is what gives the bot human-like reply timing
instead of replying the instant a message comes in.
"""
import logging

from app.ai.llm import get_ai_reply
from app.config import settings
from app.database.crud import get_or_create_thread, add_message, get_recent_messages, create_scheduled_message
from app.database.database import get_session
from app.services.memory import messages_to_history
from app.services.scheduler import compute_schedule, GOODNIGHT_MESSAGE

logger = logging.getLogger("conversation")


async def handle_incoming_message(sender_id: str, text: str) -> None:
    is_primary = bool(settings.PRIMARY_USER_ID) and sender_id == settings.PRIMARY_USER_ID
    if not settings.PRIMARY_USER_ID:
        is_primary = True

    async with get_session() as session:
        thread = await get_or_create_thread(session, sender_id)
        await add_message(session, thread.id, role="user", content=text)

        recent = await get_recent_messages(session, thread.id)
        history = messages_to_history(recent[:-1])  # exclude the message we just added

        last_message_at = recent[-2].created_at if len(recent) >= 2 else None

        decision = compute_schedule(last_message_at=last_message_at)

        if decision.use_goodnight_message:
            reply_text, provider = GOODNIGHT_MESSAGE, None
        else:
            reply_text, provider = await get_ai_reply(history, text, is_primary=is_primary)

        await add_message(session, thread.id, role="assistant", content=reply_text, provider=provider)

        await create_scheduled_message(
            session,
            thread_id=thread.id,
            ig_sender_id=sender_id,
            reply_text=reply_text,
            send_at=decision.send_at_utc,
            provider=provider,
        )

    logger.info(f"Scheduled reply for {sender_id} at {decision.send_at_utc} UTC")

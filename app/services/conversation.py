"""
Orchestrates a single incoming-message -> reply cycle:
load thread -> load history -> call LLM -> save assistant message -> SCHEDULE
the actual send for later (see app/services/scheduler.py) instead of sending
immediately. A cron endpoint (/cron/process-scheduled) delivers it once its
scheduled time arrives - this is what gives the bot human-like reply timing
instead of replying the instant a message comes in.

If the sender fires off several messages in a row (before the earlier ones
have actually been delivered), each one's schedule is computed independently
by default - that can invert order (a later message's "continuity" check can
fire while an earlier one is still waiting out its random delay) and can
scatter replies far apart. To avoid that, if the thread already has a
pending (not yet sent) reply queued, the new reply is chained a few seconds
after it instead, keeping the whole burst close together and in order.
"""
import logging
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta
from asyncio import Lock

from app.ai.llm import get_ai_reply
from app.database.crud import (
    get_or_create_thread,
    add_message,
    get_recent_messages,
    create_scheduled_message,
    get_last_pending_send_at,
    mark_thread_primary_confirmed,
)
from app.database.database import get_session
from app.services.memory import messages_to_history
from app.services.scheduler import compute_schedule, GOODNIGHT_MESSAGE

logger = logging.getLogger("conversation")

# Gap between replies when chaining onto an already-pending reply for the
# same thread (i.e. the sender sent multiple messages in a row).
CHAIN_GAP_SECONDS_MIN = 2
CHAIN_GAP_SECONDS_MAX = 6

# Nobody gets the "primary" persona (system.txt + persona_primary.txt) just
# by messaging the account. A thread only becomes primary once the sender
# has told the bot their name is Mohit Mishra in plain text - checked
# against every incoming message until it matches, then remembered forever
# for that thread (see is_primary_confirmed on the Thread model).
_PRIMARY_NAME_RE = re.compile(r"\bmohit\s+mishra\b", re.IGNORECASE)


def _declares_primary_name(text: str) -> bool:
    return bool(_PRIMARY_NAME_RE.search(text))


# One lock per sender - guarantees that if this person sends several
# messages close together, each one is FULLY processed (LLM call, DB write,
# scheduling) before the next one starts. Without this, two messages
# processed concurrently could finish their (variable-latency) LLM calls in
# a different order than they arrived, and the faster one would grab
# get_last_pending_send_at() before the earlier one had written anything -
# scrambling both the order and the "queue right after" chaining.
_sender_locks: dict[str, Lock] = defaultdict(Lock)


async def handle_incoming_message(sender_id: str, text: str) -> None:
    async with _sender_locks[sender_id]:
        await _handle_incoming_message_locked(sender_id, text)


async def _handle_incoming_message_locked(sender_id: str, text: str) -> None:
    async with get_session() as session:
        thread = await get_or_create_thread(session, sender_id)
        await add_message(session, thread.id, role="user", content=text)

        is_primary = thread.is_primary_confirmed
        if not is_primary and _declares_primary_name(text):
            await mark_thread_primary_confirmed(session, thread.id)
            is_primary = True
            logger.info(f"Thread {thread.id} ({sender_id}) confirmed as primary (Mohit Mishra)")

        recent = await get_recent_messages(session, thread.id)
        history = messages_to_history(recent[:-1])  # exclude the message we just added

        last_message_at = recent[-2].created_at if len(recent) >= 2 else None

        decision = compute_schedule(last_message_at=last_message_at)

        if decision.use_goodnight_message:
            reply_text, provider = GOODNIGHT_MESSAGE, None
        else:
            reply_text, provider = await get_ai_reply(history, text, is_primary=is_primary)

        await add_message(session, thread.id, role="assistant", content=reply_text, provider=provider)

        # If this thread already has a reply queued that hasn't gone out yet,
        # chain this one right after it (small gap) so order + batching stay
        # correct regardless of what the random-delay/continuity logic above
        # decided in isolation.
        last_pending = await get_last_pending_send_at(session, thread.id)
        now_utc = datetime.utcnow()
        if last_pending is not None:
            gap = timedelta(seconds=random.randint(CHAIN_GAP_SECONDS_MIN, CHAIN_GAP_SECONDS_MAX))
            send_at = max(last_pending, now_utc) + gap
        else:
            send_at = decision.send_at_utc

        await create_scheduled_message(
            session,
            thread_id=thread.id,
            ig_sender_id=sender_id,
            reply_text=reply_text,
            send_at=send_at,
            provider=provider,
        )

    logger.info(f"Scheduled reply for {sender_id} at {send_at} UTC")

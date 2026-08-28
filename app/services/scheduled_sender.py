"""
Called by the /cron/process-scheduled endpoint (hit periodically by an
external cron ping, e.g. cron-job.org every 1-2 minutes). Finds any
ScheduledMessage rows whose send_at has passed and actually delivers them
to Instagram now.
"""
import logging
from datetime import datetime, timezone

from app.database.crud import get_due_scheduled_messages, mark_scheduled_status
from app.database.database import get_session
from app.services.instagram import send_message, send_typing_indicator

logger = logging.getLogger("scheduled_sender")

# If a scheduled reply has been sitting unsent for longer than this (e.g. the
# server was asleep/down for a while), skip it instead of dumping a burst of
# stale old replies all at once when the app wakes back up.
STALE_THRESHOLD_MINUTES = 120


async def process_due_messages() -> dict:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sent = 0
    failed = 0
    skipped = 0

    async with get_session() as session:
        due = await get_due_scheduled_messages(session, now)

        for sched in due:
            age_minutes = (now - sched.send_at).total_seconds() / 60
            if age_minutes > STALE_THRESHOLD_MINUTES:
                logger.warning(f"Skipping stale scheduled message {sched.id} ({age_minutes:.0f} min old)")
                await mark_scheduled_status(session, sched.id, "skipped")
                skipped += 1
                continue

            try:
                await send_typing_indicator(sched.ig_sender_id)
                await send_message(sched.ig_sender_id, sched.reply_text)
                await mark_scheduled_status(session, sched.id, "sent")
                sent += 1
            except Exception as e:
                logger.error(f"Failed to send scheduled message {sched.id}: {e}")
                await mark_scheduled_status(session, sched.id, "failed")
                failed += 1

    return {"checked_at": now.isoformat(), "sent": sent, "failed": failed, "skipped": skipped}

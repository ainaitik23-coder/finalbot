"""
Decides WHEN a reply should actually go out, based on Indian Standard Time
(IST), so the bot doesn't reply instantly like an obvious script.

Daily schedule (IST):
  01:00 - 07:00  -> quiet hours, no replies at all
  07:00 - 13:00  -> active, random delay 0-60 min
  13:00 - 14:00  -> lunch break, no replies
  14:00 - 20:00  -> active, random delay 0-60 min
  20:00 - 21:00  -> evening break, no replies
  21:00 - 00:30  -> active, random delay 0-60 min
  00:30 - 01:00  -> "going to bed" window - instead of a normal AI reply,
                     sends a fixed goodnight message, then goes quiet until 07:00

EXCEPTION - continuity: if the thread's last message (either side) was less
than CONTINUITY_THRESHOLD_MINUTES ago AND we're inside an active window,
reply immediately instead of applying the random delay - this is what makes
an ongoing back-and-forth feel natural instead of every single message
getting a random wait. Quiet hours / lunch / evening break / the bedtime
warning always apply regardless of continuity.

All internal math is done in IST, then converted to naive UTC for storage
(matching the naive-UTC columns used elsewhere in the DB).
"""
import random
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

GOODNIGHT_MESSAGE = "Ab mujhe sona hai, kal baat karungi! 🌙"

# Window boundaries, as time-of-day in IST.
QUIET_START = time(1, 0)
QUIET_END = time(7, 0)
BEDTIME_WARNING_START = time(0, 30)
LUNCH_START = time(13, 0)
LUNCH_END = time(14, 0)
EVENING_BREAK_START = time(20, 0)
EVENING_BREAK_END = time(21, 0)

MAX_DELAY_MINUTES = 60

# If the last message in the thread (either side) was more recent than this,
# treat the conversation as "ongoing" and reply immediately instead of
# applying the random delay (only inside active windows).
CONTINUITY_THRESHOLD_MINUTES = 7


@dataclass
class ScheduleDecision:
    send_at_utc: datetime  # naive UTC datetime - when the reply should be sent
    use_goodnight_message: bool  # if True, caller should send GOODNIGHT_MESSAGE instead of the AI reply


def _to_utc_naive(dt_ist: datetime) -> datetime:
    return dt_ist.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def _combine(d: date, t: time) -> datetime:
    return datetime.combine(d, t, tzinfo=IST)


def compute_schedule(
    now_utc: datetime | None = None, last_message_at: datetime | None = None
) -> ScheduleDecision:
    """
    now_utc: naive UTC datetime (defaults to current time). Pass this in
    tests; leave blank in production.
    last_message_at: naive UTC datetime of the thread's previous message
    (either side), or None if this is the first message. Used for the
    continuity exception - pass None to always use the random delay.
    """
    if now_utc is None:
        now_ist = datetime.now(IST)
        now_utc_naive = now_ist.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    else:
        now_utc_naive = now_utc
        now_ist = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)

    is_continuous = (
        last_message_at is not None
        and (now_utc_naive - last_message_at) <= timedelta(minutes=CONTINUITY_THRESHOLD_MINUTES)
    )

    t = now_ist.time()
    today = now_ist.date()
    tomorrow = today + timedelta(days=1)

    # 1. Bedtime warning window (00:30 - 01:00): fixed goodnight message,
    #    sent almost immediately, always before the 01:00 hard cutoff.
    if BEDTIME_WARNING_START <= t < QUIET_START:
        cutoff = _combine(today, QUIET_START) - timedelta(minutes=1)
        candidate = now_ist + timedelta(minutes=random.randint(0, 5))
        send_at = min(candidate, cutoff)
        return ScheduleDecision(send_at_utc=_to_utc_naive(send_at), use_goodnight_message=True)

    # 2. Quiet hours (01:00 - 07:00): defer to today's 07:00 active window.
    if QUIET_START <= t < QUIET_END:
        window_start = _combine(today, QUIET_END)
        window_end = _combine(today, LUNCH_START) - timedelta(minutes=1)
        send_at = window_start + timedelta(minutes=random.randint(0, MAX_DELAY_MINUTES))
        send_at = min(send_at, window_end)
        return ScheduleDecision(send_at_utc=_to_utc_naive(send_at), use_goodnight_message=False)

    # 3. Morning active window (07:00 - 13:00)
    if QUIET_END <= t < LUNCH_START:
        if is_continuous:
            return ScheduleDecision(send_at_utc=now_utc_naive, use_goodnight_message=False)
        window_end = _combine(today, LUNCH_START) - timedelta(minutes=1)
        send_at = now_ist + timedelta(minutes=random.randint(0, MAX_DELAY_MINUTES))
        send_at = min(send_at, window_end)
        return ScheduleDecision(send_at_utc=_to_utc_naive(send_at), use_goodnight_message=False)

    # 4. Lunch break (13:00 - 14:00): defer to 14:00 active window.
    if LUNCH_START <= t < LUNCH_END:
        window_start = _combine(today, LUNCH_END)
        window_end = _combine(today, EVENING_BREAK_START) - timedelta(minutes=1)
        send_at = window_start + timedelta(minutes=random.randint(0, MAX_DELAY_MINUTES))
        send_at = min(send_at, window_end)
        return ScheduleDecision(send_at_utc=_to_utc_naive(send_at), use_goodnight_message=False)

    # 5. Afternoon/evening active window (14:00 - 20:00)
    if LUNCH_END <= t < EVENING_BREAK_START:
        if is_continuous:
            return ScheduleDecision(send_at_utc=now_utc_naive, use_goodnight_message=False)
        window_end = _combine(today, EVENING_BREAK_START) - timedelta(minutes=1)
        send_at = now_ist + timedelta(minutes=random.randint(0, MAX_DELAY_MINUTES))
        send_at = min(send_at, window_end)
        return ScheduleDecision(send_at_utc=_to_utc_naive(send_at), use_goodnight_message=False)

    # 6. Evening break (20:00 - 21:00): defer to 21:00 active window.
    if EVENING_BREAK_START <= t < EVENING_BREAK_END:
        window_start = _combine(today, EVENING_BREAK_END)
        # the night window that follows runs until 00:30 the next day
        window_end = _combine(tomorrow, BEDTIME_WARNING_START) - timedelta(minutes=1)
        send_at = window_start + timedelta(minutes=random.randint(0, MAX_DELAY_MINUTES))
        send_at = min(send_at, window_end)
        return ScheduleDecision(send_at_utc=_to_utc_naive(send_at), use_goodnight_message=False)

    # 7. Night active window (21:00 - 00:30, crosses midnight)
    # This covers t >= 21:00 (same day) OR t < 00:30 (next day, before bedtime warning).
    if t >= EVENING_BREAK_END or t < BEDTIME_WARNING_START:
        if is_continuous:
            return ScheduleDecision(send_at_utc=now_utc_naive, use_goodnight_message=False)
        if t >= EVENING_BREAK_END:
            window_end = _combine(tomorrow, BEDTIME_WARNING_START) - timedelta(minutes=1)
        else:
            window_end = _combine(today, BEDTIME_WARNING_START) - timedelta(minutes=1)
        send_at = now_ist + timedelta(minutes=random.randint(0, MAX_DELAY_MINUTES))
        send_at = min(send_at, window_end)
        return ScheduleDecision(send_at_utc=_to_utc_naive(send_at), use_goodnight_message=False)

    # Fallback (should not reach here) - send with a small random delay.
    send_at = now_ist + timedelta(minutes=random.randint(0, MAX_DELAY_MINUTES))
    return ScheduleDecision(send_at_utc=_to_utc_naive(send_at), use_goodnight_message=False)

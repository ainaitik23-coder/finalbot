"""Database read/write operations."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Thread, Message, ScheduledMessage


async def get_or_create_thread(session: AsyncSession, ig_sender_id: str) -> Thread:
    result = await session.execute(select(Thread).where(Thread.ig_sender_id == ig_sender_id))
    thread = result.scalar_one_or_none()
    if thread is None:
        thread = Thread(ig_sender_id=ig_sender_id)
        session.add(thread)
        await session.commit()
        await session.refresh(thread)
    return thread


async def add_message(
    session: AsyncSession, thread_id: int, role: str, content: str, provider: str | None = None
) -> Message:
    msg = Message(thread_id=thread_id, role=role, content=content, provider=provider)
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


async def get_recent_messages(
    session: AsyncSession, thread_id: int, limit: int = None
) -> list[Message]:
    limit = limit or settings.MAX_HISTORY_MESSAGES
    result = await session.execute(
        select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    return messages


async def create_scheduled_message(
    session: AsyncSession,
    thread_id: int,
    ig_sender_id: str,
    reply_text: str,
    send_at: datetime,
    provider: str | None = None,
) -> ScheduledMessage:
    sched = ScheduledMessage(
        thread_id=thread_id,
        ig_sender_id=ig_sender_id,
        reply_text=reply_text,
        send_at=send_at,
        provider=provider,
        status="pending",
    )
    session.add(sched)
    await session.commit()
    await session.refresh(sched)
    return sched


async def get_due_scheduled_messages(session: AsyncSession, now: datetime) -> list[ScheduledMessage]:
    result = await session.execute(
        select(ScheduledMessage)
        .where(ScheduledMessage.status == "pending")
        .where(ScheduledMessage.send_at <= now)
        .order_by(ScheduledMessage.send_at)
    )
    return list(result.scalars().all())


async def get_last_pending_send_at(session: AsyncSession, thread_id: int) -> datetime | None:
    """
    Latest send_at among this thread's still-pending scheduled replies.
    Used to chain a new reply right after an already-queued one instead of
    letting it jump ahead (which is what caused out-of-order / all-at-once
    replies when several messages arrived close together).
    """
    result = await session.execute(
        select(ScheduledMessage.send_at)
        .where(ScheduledMessage.thread_id == thread_id)
        .where(ScheduledMessage.status == "pending")
        .order_by(ScheduledMessage.send_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def mark_thread_primary_confirmed(session: AsyncSession, thread_id: int) -> None:
    result = await session.execute(select(Thread).where(Thread.id == thread_id))
    thread = result.scalar_one_or_none()
    if thread is not None and not thread.is_primary_confirmed:
        thread.is_primary_confirmed = True
        await session.commit()


async def mark_scheduled_status(session: AsyncSession, scheduled_id: int, status: str) -> None:
    result = await session.execute(
        select(ScheduledMessage).where(ScheduledMessage.id == scheduled_id)
    )
    sched = result.scalar_one_or_none()
    if sched is not None:
        sched.status = status
        await session.commit()

"""Database read/write operations."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Thread, Message


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
    messages.reverse()  # chronological order
    return messages

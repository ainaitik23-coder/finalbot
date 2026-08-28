"""SQLAlchemy ORM models."""
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Thread(Base):
    """One thread per unique Instagram sender (i.e. per conversation)."""
    __tablename__ = "threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ig_sender_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32), nullable=True)  # e.g. "gemini", null for user msgs
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    thread: Mapped["Thread"] = relationship(back_populates="messages")


class ScheduledMessage(Base):
    """
    A reply that's been generated but is waiting for its scheduled send
    time (see app/services/scheduler.py). A background cron hits
    /cron/process-scheduled periodically to send any that are due.
    """
    __tablename__ = "scheduled_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id"), index=True)
    ig_sender_id: Mapped[str] = mapped_column(String(64), index=True)
    reply_text: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32), nullable=True)
    send_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

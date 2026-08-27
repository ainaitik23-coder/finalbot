"""Misc small helpers."""
from app.utils.constants import MAX_REPLY_CHARS


def truncate_reply(text: str, limit: int = MAX_REPLY_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

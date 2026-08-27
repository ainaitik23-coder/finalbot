"""
Converts DB Message rows into the {"role","content"} format the LLM layer expects.
"""
from app.database.models import Message


def messages_to_history(messages: list[Message]) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in messages]

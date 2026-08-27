"""Basic payload validation helpers for incoming webhook events."""
from typing import Any


def extract_messaging_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Meta webhook payload shape:
    {
      "object": "instagram",
      "entry": [
        {
          "id": "...",
          "time": ...,
          "messaging": [
            {
              "sender": {"id": "..."},
              "recipient": {"id": "..."},
              "timestamp": ...,
              "message": {"mid": "...", "text": "..."}
            }
          ]
        }
      ]
    }
    """
    events = []
    if payload.get("object") != "instagram":
        return events

    for entry in payload.get("entry", []):
        for msg_event in entry.get("messaging", []):
            events.append(msg_event)
    return events


def is_valid_text_message(event: dict[str, Any]) -> bool:
    """Filter out echoes, read receipts, reactions, deleted messages etc."""
    message = event.get("message")
    if not message:
        return False
    if message.get("is_echo"):
        return False
    if not message.get("text"):
        return False
    return True


def get_sender_id(event: dict[str, Any]) -> str | None:
    return event.get("sender", {}).get("id")


def get_message_text(event: dict[str, Any]) -> str | None:
    return event.get("message", {}).get("text")

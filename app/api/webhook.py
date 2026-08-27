"""
Receives actual DM events from Instagram (POST) after verification (GET, in verify.py)
is done. This is the main entry point for every incoming message.
"""
import logging

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks

from app.utils.security import verify_signature
from app.utils.validators import extract_messaging_events, is_valid_text_message, get_sender_id, get_message_text
from app.services.conversation import handle_incoming_message

logger = logging.getLogger("webhook")

router = APIRouter()


@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_signature(raw_body, signature):
        logger.warning("Rejected webhook: bad signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    events = extract_messaging_events(payload)

    for event in events:
        if not is_valid_text_message(event):
            continue

        sender_id = get_sender_id(event)
        text = get_message_text(event)
        if not sender_id or not text:
            continue

        # process in background so we can return 200 to Meta immediately
        # (Meta expects a fast response and will retry if you're slow)
        background_tasks.add_task(handle_incoming_message, sender_id, text)

    return {"status": "received"}

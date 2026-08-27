"""
Handles Meta's webhook GET verification handshake.
When you register the webhook URL in the Meta App dashboard, Meta sends a GET
request with these query params to confirm you own the endpoint.
"""
from fastapi import APIRouter, Request, Response, HTTPException

from app.config import settings

router = APIRouter()


@router.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.IG_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verification failed")

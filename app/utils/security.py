"""
Webhook signature verification (Meta X-Hub-Signature-256).
Without this, anyone who finds your webhook URL can send fake events.
"""
import hashlib
import hmac
import logging

from app.config import settings

logger = logging.getLogger("security")


def verify_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """
    Meta sends: X-Hub-Signature-256: sha256=<hex_digest>
    We recompute the HMAC using our app secret and compare.
    """
    if not signature_header:
        logger.warning("DEBUG: no signature header received at all")
        return False

    try:
        algo, received_hash = signature_header.split("=", 1)
    except ValueError:
        logger.warning(f"DEBUG: couldn't split signature header: {signature_header!r}")
        return False

    if algo != "sha256":
        logger.warning(f"DEBUG: unexpected algo: {algo!r}")
        return False

    expected_hash = hmac.new(
        key=settings.IG_APP_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # TEMPORARY DEBUG LOGGING - remove once this is working
    logger.warning(
        f"DEBUG: secret_len={len(settings.IG_APP_SECRET)} "
        f"secret_last4={settings.IG_APP_SECRET[-4:]!r} "
        f"expected_last8={expected_hash[-8:]} received_last8={received_hash[-8:]}"
    )

    return hmac.compare_digest(expected_hash, received_hash)

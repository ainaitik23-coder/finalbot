"""Simple health check endpoint, useful for uptime pings (e.g. cron-job.org)
to keep a free-tier host from sleeping."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}
@router.get("/privacy")
async def privacy_policy():
    return {
        "policy": "Ye ek personal/testing chatbot hai jo Instagram DMs ka reply deta hai. "
                   "Koi user data third-party ke saath share nahi kiya jata. "
                   "Data sirf conversation ke liye store hota hai."
    }

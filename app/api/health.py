"""Simple health check endpoint, useful for uptime pings (e.g. cron-job.org)
to keep a free-tier host from sleeping."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}

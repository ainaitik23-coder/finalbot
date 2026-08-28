"""
Endpoint an external cron pings periodically (e.g. cron-job.org every 1-2
minutes) to deliver any replies that have become due. This is what makes
the random-delay/quiet-hours scheduling actually work in production -
without an external ping, nothing would trigger delivery once the app is
just sitting idle.
"""
from fastapi import APIRouter

from app.services.scheduled_sender import process_due_messages

router = APIRouter()


@router.get("/cron/process-scheduled")
async def process_scheduled():
    result = await process_due_messages()
    return result

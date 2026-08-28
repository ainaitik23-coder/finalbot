"""FastAPI app entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import webhook, verify, health, cron
from app.database.database import init_db
from app.services.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_db()
    yield


app = FastAPI(title="Instagram AI Bot", lifespan=lifespan)

app.include_router(verify.router)
app.include_router(webhook.router)
app.include_router(health.router)
app.include_router(cron.router)


@app.get("/")
async def root():
    return {"status": "running"}

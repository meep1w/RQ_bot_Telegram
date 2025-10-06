from fastapi import FastAPI
from app.routers.ga_webhook import router as ga_router
from app.routers.child_webhook import router as child_router
from app.settings import settings
from app.services.webhooks import set_ga_webhook
from aiogram import Bot

app = FastAPI(title="Multi-tenant JoinBot")

@app.get("/health")
async def health():
    return {"ok": True}

app.include_router(ga_router)
app.include_router(child_router)

@app.on_event("startup")
async def on_startup():
    if settings.USE_WEBHOOK:
        bot = Bot(settings.GA_BOT_TOKEN)
        await set_ga_webhook(bot)

from fastapi import APIRouter, Request, Response
from aiogram import Bot
from aiogram.types import Update
from app.settings import settings
from app.bots.dispatcher import make_dp
from app.bots import ga_bot

router = APIRouter()
_bot = Bot(settings.GA_BOT_TOKEN)
_dp = make_dp()
_dp.include_router(ga_bot.router)

@router.post("/webhook/ga")
async def webhook_ga(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await _dp.feed_update(_bot, update)
    return Response(status_code=200)

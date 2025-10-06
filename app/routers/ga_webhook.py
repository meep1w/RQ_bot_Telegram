from fastapi import APIRouter, Request, Response, Depends
from aiogram import Bot
from app.settings import settings
from app.bots.dispatcher import make_dp
from app.bots import ga_bot

router = APIRouter()

# Инициализируем GA бота/диспетчер один раз
_ga_bot = Bot(settings.GA_BOT_TOKEN)
_ga_dp = make_dp()
_ga_dp.include_router(ga_bot.router)

@router.post("/webhook/ga")
async def webhook_ga(request: Request):
    data = await request.json()
    update = _ga_dp.event_factory.update(data)
    await _ga_dp.feed_update(_ga_bot, update)
    return Response(status_code=200)
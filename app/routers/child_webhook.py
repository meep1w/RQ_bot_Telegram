# app/routers/child_webhook.py
from fastapi import APIRouter, Request, Response, HTTPException
from aiogram import Bot
from aiogram.types import Update
from app.bots.dispatcher import make_dp
from app.bots import child_bot
from app.db import AsyncSessionLocal
from app.models import Tenant
from app.bots.middlewares.tenant_ctx import TenantContext

router = APIRouter()

dp = make_dp()
dp.include_router(child_bot.router)
# важно: вешаем на ВСЕ события (update) — покроет и callback_query
dp.update.middleware(TenantContext())

_child_bots: dict[int, Bot] = {}

async def _get_bot_for(tenant_id: int) -> Bot:
    if tenant_id in _child_bots:
        return _child_bots[tenant_id]
    async with AsyncSessionLocal() as s:
        t = await s.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(404, "Tenant not found")
    b = Bot(t.bot_token)
    _child_bots[tenant_id] = b
    return b

@router.post("/webhook/child/{tenant_id}/{secret}")
async def webhook_child(tenant_id: int, secret: str, request: Request):
    # получаем тенанта
    async with AsyncSessionLocal() as s:
        t = await s.get(Tenant, tenant_id)
    if not t or not t.is_active or t.secret != secret:
        raise HTTPException(403, "Forbidden")

    bot = await _get_bot_for(tenant_id)

    # подложим «легкий» словарь в объект бота – middleware его подцепит
    bot._tenant = {"id": t.id, "owner_user_id": t.owner_user_id}

    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return Response(status_code=200)

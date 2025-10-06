from fastapi import APIRouter, Request, Response, HTTPException
from aiogram import Bot
from sqlalchemy import select
from app.bots.dispatcher import make_dp
from app.bots import child_bot
from app.db import AsyncSessionLocal
from app.models import Tenant

router = APIRouter()

# Кеш для ботов по tenant_id
_child_bots: dict[int, Bot] = {}
_child_dps = make_dp()
_child_dps.include_router(child_bot.router)

async def get_child_bot(tenant_id: int) -> Bot:
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
    async with AsyncSessionLocal() as s:
        t = await s.get(Tenant, tenant_id)
    if not t or t.secret != secret or not t.is_active:
        raise HTTPException(403, "Forbidden")
    bot = await get_child_bot(tenant_id)
    data = await request.json()
    update = _child_dps.event_factory.update(data)
    # TODO: middleware для tenant_id в контекст
    await _child_dps.feed_update(bot, update)
    return Response(status_code=200)
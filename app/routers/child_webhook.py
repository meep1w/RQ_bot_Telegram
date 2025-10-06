from fastapi import APIRouter, Request, Response, HTTPException
from aiogram import Bot
from aiogram.types import Update
from app.bots.dispatcher import make_dp
from app.bots.child_bot import router as child_router
from app.bots.middlewares.tenant_ctx import TenantContext
from app.services.tenants_simple import get_tenant

router = APIRouter()

_TENANT_BOTS: dict[int, Bot] = {}
_TENANT_DPS = {}  # dispatcher per tenant

def _get_or_create_dp(tenant: dict):
    tid = tenant["id"]
    dp = _TENANT_DPS.get(tid)
    if dp:
        return dp
    dp = make_dp()
    # кладём tenant в data и для сообщений, и для callback_query
    dp.message.middleware(TenantContext(tenant))
    dp.callback_query.middleware(TenantContext(tenant))
    dp.include_router(child_router)
    _TENANT_DPS[tid] = dp
    return dp

def _get_or_create_bot(tenant: dict):
    tid = tenant["id"]
    bot = _TENANT_BOTS.get(tid)
    if bot:
        return bot
    bot = Bot(tenant["bot_token"])
    _TENANT_BOTS[tid] = bot
    return bot

@router.post("/webhook/child/{tenant_id:int}/{secret}")
async def webhook_child(tenant_id: int, secret: str, request: Request):
    tenant = await get_tenant(tenant_id)
    if not tenant or tenant.get("secret") != secret or not tenant.get("is_active", True):
        raise HTTPException(403, "Forbidden")

    data = await request.json()
    update = Update.model_validate(data)

    dp = _get_or_create_dp(tenant)
    bot = _get_or_create_bot(tenant)

    await dp.feed_update(bot, update)
    return Response(status_code=200)

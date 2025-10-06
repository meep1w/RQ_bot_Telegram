# app/bots/middlewares/tenant_ctx.py
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

class TenantContext(BaseMiddleware):
    def __init__(self, tenant_id_getter):
        self.tenant_id_getter = tenant_id_getter

    async def __call__(self, handler: Callable[[Dict[str, Any], Any], Awaitable[Any]], event, data):
        data["tenant_id"] = await self.tenant_id_getter(event)
        return await handler(event, data)
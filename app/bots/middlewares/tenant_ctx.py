# app/bots/middlewares/tenant_ctx.py
from aiogram import BaseMiddleware
from typing import Callable, Any, Awaitable, Dict

class TenantContext(BaseMiddleware):
    """
    Кладём в data["tenant"] объект, который заранее положили в bot._tenant.
    Работает для message/callback_query/chat_join_request/chat_member и т.д.
    """
    async def __call__(
        self,
        handler: Callable[[Dict[str, Any], Any], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        tenant = getattr(getattr(event, "bot", None), "_tenant", None)
        if tenant:
            data["tenant"] = tenant
        return await handler(event, data)

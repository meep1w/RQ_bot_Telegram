# app/bots/middlewares/tenant_ctx.py
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware

class TenantContext(BaseMiddleware):
    """
    Кладёт dict tenant в data для любых событий (message, callback_query и т.д.).
    Раньше тут ждали callable; теперь принимаем готовый dict.
    """
    def __init__(self, tenant: Dict[str, Any]):
        self.tenant = tenant

    async def __call__(
        self,
        handler: Callable[[Dict[str, Any], Any], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        data["tenant"] = self.tenant
        return await handler(event, data)

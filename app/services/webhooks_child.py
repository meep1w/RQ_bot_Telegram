from aiogram import Bot
from aiogram.types import FSInputFile
from app.settings import settings

CERT_PATH = "/etc/ssl/certs/multibot.crt"

async def set_child_webhook(bot: Bot, tenant_id: int, secret: str):
    cert = FSInputFile(CERT_PATH)
    await bot.set_webhook(
        url=f"{settings.WEB_BASE}/webhook/child/{tenant_id}/{secret}",
        drop_pending_updates=True,
        allowed_updates=["message","callback_query","chat_join_request","chat_member","my_chat_member"],
        certificate=cert,
    )

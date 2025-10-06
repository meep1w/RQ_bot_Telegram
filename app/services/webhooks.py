from aiogram import Bot
from aiogram.types import FSInputFile
from app.settings import settings

async def set_ga_webhook(bot: Bot):
    cert = FSInputFile(settings.CERT_PATH)
    await bot.set_webhook(
        url=f"{settings.WEB_BASE}/webhook/ga",
        drop_pending_updates=True,
        allowed_updates=["message","callback_query","chat_join_request","chat_member","my_chat_member","chat_member_updated"],
        certificate=cert,
    )

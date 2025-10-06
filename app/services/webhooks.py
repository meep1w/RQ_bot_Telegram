from aiogram.types import FSInputFile

async def set_ga_webhook(bot: Bot):
    cert = FSInputFile("/etc/ssl/certs/multibot.crt")
    await bot.set_webhook(
        url=f"{settings.WEB_BASE}/webhook/ga",
        drop_pending_updates=True,
        allowed_updates=["message","callback_query","chat_join_request","chat_member","my_chat_member","chat_member_updated"],
        certificate=cert,
    )

async def set_child_webhook(bot: Bot, tenant_id: int, secret: str):
    cert = FSInputFile("/etc/ssl/certs/multibot.crt")
    await bot.set_webhook(
        url=f"{settings.WEB_BASE}/webhook/child/{tenant_id}/{secret}",
        drop_pending_updates=True,
        allowed_updates=["message","callback_query","chat_join_request","chat_member","my_chat_member"],
        certificate=cert,
    )

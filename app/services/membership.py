from aiogram import Bot
from app.settings import settings

async def is_in_group(bot: Bot, user_id: int) -> bool:
    try:
        cm = await bot.get_chat_member(settings.GROUP_ID, user_id)
        return getattr(cm, "status", None) in {"creator", "administrator", "member"}
    except Exception:
        return False

from aiogram import Bot
from app.settings import settings

async def is_owner_in_group(bot: Bot, owner_user_id: int) -> bool:
    try:
        cm = await bot.get_chat_member(settings.GROUP_ID, owner_user_id)
        status = getattr(cm, "status", None)
        return status in {"creator", "administrator", "member"}
    except Exception:
        return False
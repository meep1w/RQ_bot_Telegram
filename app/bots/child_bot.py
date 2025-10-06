from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ChatJoinRequest, ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.bots.common import child_admin_kb
from app.db import AsyncSessionLocal
from app.models import Tenant, ChannelLink, Greeting, StatDaily

router = Router()

@router.message(Command("admin"))
async def child_admin(msg: Message, bot: Bot):
    # простая проверка: владелец ли он? (по идее из middleware можно резолвить tenant)
    await msg.answer("Админ меню", reply_markup=child_admin_kb())

# === Пример: авто‑аппрув заявок ===
@router.chat_join_request()
async def on_join_request(evt: ChatJoinRequest, bot: Bot):
    try:
        await bot.approve_chat_join_request(evt.chat.id, evt.from_user.id)
        # учёт статистики
        day = datetime.utcnow().strftime("%Y-%m-%d")
        async with AsyncSessionLocal() as s:
            await s.execute("""
                INSERT INTO stats_daily (tenant_id, day, joins, leaves, approvals)
                VALUES (:tid, :day, 0, 0, 1)
                ON CONFLICT (tenant_id, day) DO UPDATE SET approvals = stats_daily.approvals + 1
            """, {"tid": 0, "day": day})  # TODO: подставить tenant_id через middleware
            await s.commit()
    except Exception:
        pass

# === Пример: сообщение при выходе ===
@router.chat_member()
async def on_chat_member(evt: ChatMemberUpdated, bot: Bot):
    try:
        if evt.old_chat_member and evt.new_chat_member:
            old = evt.old_chat_member.status
            new = evt.new_chat_member.status
            if old in {"member"} and new in {"left", "kicked"}:
                # отправим прощание в чат, если включено
                await bot.send_message(evt.chat.id, "Пользователь покинул чат. До встречи!")
                # учёт статистики
                day = datetime.utcnow().strftime("%Y-%m-%d")
                async with AsyncSessionLocal() as s:
                    await s.execute("""
                        INSERT INTO stats_daily (tenant_id, day, joins, leaves, approvals)
                        VALUES (:tid, :day, 0, 1, 0)
                        ON CONFLICT (tenant_id, day) DO UPDATE SET leaves = stats_daily.leaves + 1
                    """, {"tid": 0, "day": day})  # TODO: tenant_id через middleware
                    await s.commit()
    except Exception:
        pass
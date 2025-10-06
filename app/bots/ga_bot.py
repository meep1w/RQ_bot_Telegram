from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import ADMIN_IDS, settings
from app.bots.common import ga_main_kb, ga_clients_page_kb, tenant_card_kb
from app.services.tenants import create_or_replace_tenant, get_tenant_by_id, delete_tenant
from app.services.webhooks import set_child_webhook
from app.services.membership import is_owner_in_group
from app.db import AsyncSessionLocal
from app.models import Tenant

router = Router()

@router.message(Command("start"))
async def ga_start(msg: Message, bot: Bot):
    uid = msg.from_user.id
    in_group = await is_owner_in_group(bot, uid)
    if in_group:
        await msg.answer("Привет! Отправь мне API‑Token своего бота, я подключу его.\nВажно: 1 человек → 1 бот.")
    else:
        await msg.answer("Привет! Похоже, ты не участник приватного канала. Напиши @toffadds, чтобы узнать условия.")

# Принимаем токен бота от участника приватки
@router.message(F.text.regexp(r"\d{9,10}:[A-Za-z0-9_-]{35,}"))
async def receive_bot_token(msg: Message, bot: Bot):
    uid = msg.from_user.id
    if not await is_owner_in_group(bot, uid):
        await msg.answer("Ты не состоишь в приватном канале. Напиши @toffadds.")
        return

    token = msg.text.strip()
    username = msg.from_user.username
    async with AsyncSessionLocal() as session:
        tenant = await create_or_replace_tenant(session, uid, username, token)
        await session.commit()

    # Поставим вебхук для дочернего бота и сохраним username
    cbot = Bot(token)
    me = await cbot.get_me()
    async with AsyncSessionLocal() as session:
        t = await session.get(Tenant, tenant.id)
        t.bot_username = me.username
        await session.commit()
    from app.services.webhooks import set_child_webhook
    await set_child_webhook(cbot, tenant.id, t.secret)

    await msg.answer(f"Ваш бот успешно подключен! Перейдите к нему и завершите настройку: @{me.username}")

@router.message(Command("ga"))
async def ga_admin_menu(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.answer("Окно Главный Админ", reply_markup=ga_main_kb())

@router.callback_query(F.data.startswith("ga:clients:"))
async def ga_clients_list(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer()
    page = int(cb.data.split(":")[-1])
    page_size = 10
    offset = (page-1)*page_size

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            """
            SELECT id, owner_user_id, owner_username, bot_username, is_active
            FROM tenants ORDER BY id DESC LIMIT :lim OFFSET :off
            """,
            {"lim": page_size+1, "off": offset}
        )
        rows = res.fetchall()
    has_next = len(rows) > page_size
    rows = rows[:page_size]
    text = "Список клиентов:\n" + "\n".join(
        [f"• #{r.id} @{r.bot_username or '-'} (owner: @{r.owner_username or r.owner_user_id}) /tenant_{r.id}" for r in rows]
    )
    await cb.message.edit_text(text, reply_markup=ga_clients_page_kb(page, page>1, has_next))
    await cb.answer()

@router.message(F.text.regexp(r"/tenant_(\d+)"))
async def ga_tenant_card(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    tenant_id = int(msg.text.split("_")[-1])
    async with AsyncSessionLocal() as session:
        t = await get_tenant_by_id(session, tenant_id)
    if not t:
        return await msg.answer("Не найден")
    text = (
        f"Тенант #{t.id}\n"
        f"Владелец: @{t.owner_username or t.owner_user_id}\n"
        f"Бот: @{t.bot_username or '-'}\n"
        f"Статус: {'Активен' if t.is_active else 'Выключен'}\n"
    )
    await msg.answer(text, reply_markup=tenant_card_kb(t.id))

@router.callback_query(F.data.startswith("ga:tenant:"))
async def ga_tenant_actions(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer()
    _, _, tid, action = cb.data.split(":")
    tid = int(tid)
    if action == "delete":
        async with AsyncSessionLocal() as session:
            await delete_tenant(session, tid)
            await session.commit()
        await cb.message.edit_text("Клиент удалён, его бот остановлен. Можно подключить нового через GA‑бота.")
    await cb.answer()
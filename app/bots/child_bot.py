from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bots.common import child_admin_kb, channels_list_kb
from app.services.channels_simple import delete_channel, list_channels, upsert_channel

router = Router()


# ====== /admin ======

@router.message(Command("admin"))
async def child_admin(msg: Message, bot: Bot, **data):
    tenant = data.get("tenant")
    if not tenant:
        return await msg.answer("⚠️ Контекст тенанта недоступен. Напишите администратору.")
    if msg.from_user.id != tenant["owner_user_id"]:
        return await msg.answer("⛔️ Доступ к /admin только у владельца этого бота.")

    await msg.answer("Админ меню", reply_markup=child_admin_kb())


# ====== Кнопка «Назад в меню» ======

@router.callback_query(F.data == "child:back")
async def child_back(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)

    await cb.message.edit_text("Админ меню")
    await cb.message.edit_reply_markup(reply_markup=child_admin_kb())
    await cb.answer()


# ====== Экран «Чаты/Каналы» ======

@router.callback_query(F.data == "child:chats")
async def child_chats(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)

    items = await list_channels(tenant["id"])
    await cb.message.edit_text("Подключённые чаты/каналы:")
    await cb.message.edit_reply_markup(reply_markup=channels_list_kb(items))
    await cb.answer()


@router.callback_query(F.data == "child:chadd")
async def child_ch_add(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)

    text = (
        "🔗 Подключение чата/канала\n\n"
        "1) Добавьте этого бота админом в нужный чат/канал.\n"
        "2) В том чате отправьте команду: /link\n\n"
        "После этого чат появится в списке."
    )
    items = await list_channels(tenant["id"])
    await cb.message.edit_text(text)
    await cb.message.edit_reply_markup(reply_markup=channels_list_kb(items))
    await cb.answer()


@router.callback_query(F.data.startswith("child:chdel:"))
async def child_ch_delete(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)

    ch_id = int(cb.data.split(":")[-1])
    await delete_channel(tenant["id"], ch_id)

    items = await list_channels(tenant["id"])
    await cb.message.edit_text("Подключённые чаты/каналы: (удалено)")
    await cb.message.edit_reply_markup(reply_markup=channels_list_kb(items))
    await cb.answer()


# ====== /link — пишем в самом чате/канале ======

@router.message(Command("link"))
async def link_here(msg: Message, bot: Bot, **data):
    """
    Эту команду пишем ВНУТРИ целевого чата/канала, где бот уже админ.
    Сохраняем chat_id и title для текущего tenant.
    """
    tenant = data.get("tenant")
    if not tenant:
        # Чтобы бот не спамил, если хук прилетел не для нашего tenancy
        return

    # Регистрирует только владелец
    if msg.from_user and msg.from_user.id != tenant["owner_user_id"]:
        return

    chat = await bot.get_chat(msg.chat.id)
    await upsert_channel(tenant["id"], chat.id, chat.title)

    await msg.reply("✅ Чат подключён и сохранён! Вернитесь в личные сообщения и обновите список в «Чаты/Каналы».")

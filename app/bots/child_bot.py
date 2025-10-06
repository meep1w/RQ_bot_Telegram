from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from app.bots.common import child_admin_kb, channels_list_kb
from app.services.channels_simple import list_channels, upsert_channel, delete_channel

from app.bots.common import child_admin_kb

router = Router()

@router.message(Command("admin"))
async def child_admin(msg: Message, bot: Bot, **data):
    """
    Раньше мы требовали аргумент tenant: dict через middleware и молча return-или.
    Теперь: аккуратно достаем из data, отвечаем пользователю в любом случае.
    """
    tenant = data.get("tenant")
    if not tenant:
        # middleware не подложил tenant — сообщим явно
        return await msg.answer("⚠️ Контекст тенанта недоступен. Попробуйте ещё раз или напишите администратору.")

    if msg.from_user.id != tenant["owner_user_id"]:
        return await msg.answer("⛔️ Доступ к /admin только у владельца этого бота.")

    await msg.answer("Админ меню", reply_markup=child_admin_kb())

@router.callback_query(F.data.startswith("child:"))
async def child_menu_actions(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant:
        await cb.answer("Нет контекста тенанта", show_alert=True)
        return
    if cb.from_user.id != tenant["owner_user_id"]:
        await cb.answer("Только владелец", show_alert=True)
        return

    action = cb.data.split(":", 1)[1]
    mapping = {
        "chats": "Подключение чатов/каналов — скоро добавим.",
        "hello": "Приветствие — редактор шаблона (текст/кнопка/медиа) скоро добавим.",
        "bye": "Прощание — редактор шаблона скоро добавим.",
        "settings": "Настройки: Копить заявки / Собрать заявки — в работе.",
        "broadcast": "Рассылка — в работе.",
        "stats": "Статистика — в работе.",
    }
    await cb.message.edit_text(f"📌 {mapping.get(action, 'Раздел в разработке')}\n\nНажми /admin, чтобы вернуться в меню.")
    await cb.answer()

@router.callback_query(F.data == "child:back")
async def child_back(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    await cb.message.edit_text("Админ меню")
    await cb.message.edit_reply_markup(reply_markup=child_admin_kb())
    await cb.answer()

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
        "Я сохраню чат и он появится в списке."
    )
    await cb.message.edit_text(text)
    await cb.message.edit_reply_markup(reply_markup=channels_list_kb(await list_channels(tenant["id"])))
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

# === Команда /link в самом чате или канале ===
@router.message(Command("link"))
async def link_here(msg: Message, bot: Bot, **data):
    """
    Эту команду пишем ВНУТРИ чата/канала, где бот уже админ.
    """
    tenant = data.get("tenant")
    # Для апдейтов из групп middleware тоже работает, так как мы кладём tenant на dp целиком.
    if not tenant:
        return  # нам важно не спамить в чужих апдейтах

    # Только владелец может регистрировать
    if msg.from_user.id != tenant["owner_user_id"]:
        return

    chat = await bot.get_chat(msg.chat.id)
    await upsert_channel(tenant["id"], chat.id, chat.title)
    await msg.reply("✅ Чат подключён и сохранён! Вернитесь в ЛС и обновите список в «Чаты/Каналы».")
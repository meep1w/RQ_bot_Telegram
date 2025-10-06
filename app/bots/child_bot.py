from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.bots.common import child_admin_kb, channels_list_kb
from app.services.channels_simple import delete_channel, list_channels, upsert_channel

router = Router()


# ====== FSM для ввода chat_id / @username ======
class AddChatSG(StatesGroup):
    waiting_chat = State()


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


# ====== Подключить чат (без /link, через ввод chat_id/@username) ======

@router.callback_query(F.data == "child:chadd")
async def child_ch_add(cb: CallbackQuery, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)

    await state.set_state(AddChatSG.waiting_chat)
    text = (
        "🔗 Подключение чата/канала\n\n"
        "1) Добавьте этого бота админом в нужный чат/канал.\n"
        "2) Пришлите сюда *ID* (например `-1001234567890`) **или** `@username` канала/чата.\n\n"
        "Команда для отмены: /cancel"
    )
    await cb.message.edit_text(text, parse_mode="Markdown")
    await cb.answer()


@router.message(AddChatSG.waiting_chat)
async def add_chat_receive(msg: Message, bot: Bot, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant:
        return await msg.answer("⚠️ Нет контекста тенанта, попробуйте позже.")

    # Владелец?
    if msg.from_user.id != tenant["owner_user_id"]:
        return await msg.answer("⛔️ Только владелец может подключать чаты.")

    raw = (msg.text or "").strip()
    if not raw:
        return await msg.answer("Пришлите ID (например -1001234567890) или @username канала/чата.")

    # Определим идентификатор
    identifier = None
    if raw.startswith("@"):
        identifier = raw  # username
    else:
        # пробуем как int id
        try:
            identifier = int(raw)
        except ValueError:
            return await msg.answer("Неверный формат. Пришлите ID (например -1001234567890) или @username.")

    # Получим чат
    try:
        chat = await bot.get_chat(identifier)
    except Exception as e:
        return await msg.answer(
            f"Не удалось получить чат по '{raw}'. Убедитесь, что бот добавлен в канал/чат. Ошибка: {e}")

    # Проверим права бота
    try:
        me = await bot.get_me()
        cm = await bot.get_chat_member(chat.id, me.id)
        status = getattr(cm, "status", "")
        if status not in {"administrator", "creator"}:
            return await msg.answer(
                "Бот не администратор в этом чате/канале.\n"
                "Добавьте бота *админом* и пришлите ID/username снова.",
                parse_mode="Markdown",
            )
    except Exception:
        # Если не можем проверить — скорее всего бота нет в чате
        return await msg.answer(
            "Не удалось проверить права в чате. Добавьте бота админом и пришлите ID/username снова."
        )

    # Сохраняем
    await upsert_channel(tenant["id"], chat.id, chat.title)

    await state.clear()
    items = await list_channels(tenant["id"])
    await msg.answer("✅ Чат подключён и сохранён! Список обновлён.", reply_markup=channels_list_kb(items))


# ====== Отмена ввода ======

@router.message(Command("cancel"))
async def add_chat_cancel(msg: Message, state: FSMContext, **data):
    await state.clear()
    await msg.answer("Отменено. Вернитесь в /admin.")


# ====== Удаление подключённого чата ======

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

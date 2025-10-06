from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.bots.common import child_admin_kb, channels_list_kb
from app.services.channels_simple import delete_channel, list_channels, upsert_channel
from app.services.greetings_simple import get_greeting, upsert_greeting
from app.services.channels_simple import is_tenant_chat

router = Router()

# ====== FSM ======
class AddChatSG(StatesGroup):
    waiting_chat = State()

class HelloSG(StatesGroup):
    waiting_text = State()
    waiting_button = State()

class ByeSG(StatesGroup):
    waiting_text = State()
    waiting_button = State()

# ====== /admin ======
@router.message(Command("admin"))
async def child_admin(msg: Message, bot: Bot, **data):
    tenant = data.get("tenant")
    if not tenant:
        return await msg.answer("⚠️ Контекст тенанта недоступен.")
    if msg.from_user.id != tenant["owner_user_id"]:
        return await msg.answer("⛔️ Только владелец.")

    await msg.answer("Админ меню", reply_markup=child_admin_kb())

# ====== «Назад» ======
@router.callback_query(F.data == "child:back")
async def child_back(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    await cb.message.edit_text("Админ меню")
    await cb.message.edit_reply_markup(reply_markup=child_admin_kb())
    await cb.answer()

# ====== Чаты/Каналы ======
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
async def child_ch_add(cb: CallbackQuery, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    await state.set_state(AddChatSG.waiting_chat)
    text = (
        "🔗 Подключение чата/канала\n\n"
        "1) Добавьте этого бота админом в нужный чат/канал.\n"
        "2) Пришлите сюда *ID* (например `-1001234567890`) **или** `@username` канала/чата.\n\n"
        "Команда: /cancel"
    )
    await cb.message.edit_text(text, parse_mode="Markdown")
    await cb.answer()

@router.message(AddChatSG.waiting_chat)
async def add_chat_receive(msg: Message, bot: Bot, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant:
        return await msg.answer("⚠️ Нет контекста.")
    if msg.from_user.id != tenant["owner_user_id"]:
        return await msg.answer("⛔️ Только владелец.")

    raw = (msg.text or "").strip()
    if not raw:
        return await msg.answer("Пришлите ID (например -1001234567890) или @username.")

    if raw.startswith("@"):
        identifier = raw
    else:
        try:
            identifier = int(raw)
        except ValueError:
            return await msg.answer("Неверный формат. Пример: -1001234567890 или @username")

    try:
        chat = await bot.get_chat(identifier)
    except Exception as e:
        return await msg.answer(f"Не удалось получить чат по '{raw}'. Ошибка: {e}")

    try:
        me = await bot.get_me()
        cm = await bot.get_chat_member(chat.id, me.id)
        if getattr(cm, "status", "") not in {"administrator", "creator"}:
            return await msg.answer("Бот не админ. Сделайте бота админом и пришлите ещё раз.")
    except Exception:
        return await msg.answer("Не удалось проверить права. Убедитесь, что бот добавлен админом.")

    await upsert_channel(tenant["id"], chat.id, chat.title)
    await state.clear()
    items = await list_channels(tenant["id"])
    await msg.answer("✅ Чат подключён и сохранён! Список обновлён.", reply_markup=channels_list_kb(items))

@router.message(Command("cancel"))
async def add_chat_cancel(msg: Message, state: FSMContext, **data):
    await state.clear()
    await msg.answer("Отменено. Вернитесь в /admin.")

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

# ====== Приветствие / Прощание (редактор) ======
def _greet_editor_kb(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"child:{kind}:edit")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="child:back")],
    ])

@router.callback_query(F.data == "child:hello")
async def hello_open(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    g = await get_greeting(tenant["id"], "hello")
    text = g["text"] if g and g.get("text") else "— текст не задан —"
    await cb.message.edit_text(f"👋 Приветствие:\n\n{text}", reply_markup=_greet_editor_kb("hello"))
    await cb.answer()

@router.callback_query(F.data == "child:bye")
async def bye_open(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    g = await get_greeting(tenant["id"], "bye")
    text = g["text"] if g and g.get("text") else "— текст не задан —"
    await cb.message.edit_text(f"🧹 Прощание:\n\n{text}", reply_markup=_greet_editor_kb("bye"))
    await cb.answer()

@router.callback_query(F.data == "child:hello:edit")
async def hello_edit_start(cb: CallbackQuery, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    await state.set_state(HelloSG.waiting_text)
    await cb.message.edit_text("Отправьте текст приветствия (HTML формат телеграма поддерживается).")
    await cb.answer()

@router.message(HelloSG.waiting_text)
async def hello_save(msg: Message, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant:
        return await msg.answer("⚠️ Нет контекста.")
    await upsert_greeting(tenant["id"], "hello", msg.html_text or msg.text or "")
    await state.clear()
    await msg.answer("✅ Приветствие сохранено. /admin")

@router.callback_query(F.data == "child:bye:edit")
async def bye_edit_start(cb: CallbackQuery, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    await state.set_state(ByeSG.waiting_text)
    await cb.message.edit_text("Отправьте текст прощания (HTML формат телеграма поддерживается).")
    await cb.answer()

@router.message(ByeSG.waiting_text)
async def bye_save(msg: Message, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant:
        return await msg.answer("⚠️ Нет контекста.")
    await upsert_greeting(tenant["id"], "bye", msg.html_text or msg.text or "")
    await state.clear()
    await msg.answer("✅ Прощание сохранено. /admin")

# ====== Автопринятие заявок + ЛС приветствие ======
@router.chat_join_request()
async def on_join_request(event, bot: Bot, **data):
    """
    Автопринятие заявок только для чатов текущего тенанта.
    После approve отправляем приветствие в ЛС.
    """
    tenant = data.get("tenant")
    if not tenant:
        return
    chat_id = event.chat.id
    user_id = event.from_user.id

    if not await is_tenant_chat(tenant["id"], chat_id):
        return

    try:
        await bot.approve_chat_join_request(chat_id, user_id)
    except Exception:
        return

    g = await get_greeting(tenant["id"], "hello")
    if not g or not g.get("text"):
        return
    try:
        await bot.send_message(user_id, g["text"], parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        # юзер не стартовал бота / заблокировал — игнор
        pass

# ====== ЛС прощание при выходе ======
@router.chat_member()
async def on_chat_member(evt, bot: Bot, **data):
    tenant = data.get("tenant")
    if not tenant:
        return

    if not await is_tenant_chat(tenant["id"], evt.chat.id):
        return

    try:
        old = getattr(evt.old_chat_member, "status", "")
        new = getattr(evt.new_chat_member, "status", "")
    except Exception:
        return

    if old in {"member"} and new in {"left", "kicked"}:
        g = await get_greeting(tenant["id"], "bye")
        if not g or not g.get("text"):
            return
        user_id = evt.from_user.id if evt.from_user else None
        if not user_id:
            return
        try:
            await bot.send_message(user_id, g["text"], parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            pass

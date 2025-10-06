from __future__ import annotations
from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.bots.common import child_admin_kb, channels_list_kb
from app.services.channels_simple import delete_channel, list_channels, upsert_channel, is_tenant_chat
from app.services.greetings_simple import (
    get_greeting, set_text, set_photo, set_video, set_video_note,
    clear_media, set_button_start, set_button_url, clear_button
)

router = Router()

# ========= FSM =========
class AddChatSG(StatesGroup):
    waiting_chat = State()

class GreetSG(StatesGroup):
    # kind хранится в FSM data: "hello" | "bye"
    wait_text = State()
    wait_photo = State()       # ожидаем photo/file_id
    wait_video = State()
    wait_note = State()
    wait_btn_text = State()
    wait_btn_mode = State()
    wait_btn_url = State()


# ========= /admin =========
@router.message(Command("admin"))
async def child_admin(msg: Message, bot: Bot, **data):
    tenant = data.get("tenant")
    if not tenant:
        return await msg.answer("⚠️ Контекст тенанта недоступен.")
    if msg.from_user.id != tenant["owner_user_id"]:
        return await msg.answer("⛔️ Только владелец.")
    await msg.answer("Админ меню", reply_markup=child_admin_kb())


# ========= back =========
@router.callback_query(F.data == "child:back")
async def child_back(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    await cb.message.edit_text("Админ меню")
    await cb.message.edit_reply_markup(reply_markup=child_admin_kb())
    await cb.answer()


# ========= Чаты/Каналы =========
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
            return await msg.answer("Бот не админ. Сделай бота админом и пришли ещё раз.")
    except Exception:
        return await msg.answer("Не удалось проверить права. Убедись, что бот добавлен админом.")

    await upsert_channel(tenant["id"], chat.id, chat.title)
    await state.clear()
    items = await list_channels(tenant["id"])
    await msg.answer("✅ Чат подключён и сохранён! Список обновлён.", reply_markup=channels_list_kb(items))


@router.message(Command("cancel"))
async def add_chat_cancel(msg: Message, state: FSMContext, **data):
    await state.clear()
    await msg.answer("Отменено. Вернись в /admin.")


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


# ========= Редактор приветствия/прощания =========
def _editor_kb(kind: str) -> InlineKeyboardMarkup:
    # kind: "hello" | "bye"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Текст", callback_data=f"child:{kind}:text"),
            InlineKeyboardButton(text="🖼 Фото",  callback_data=f"child:{kind}:photo"),
        ],
        [
            InlineKeyboardButton(text="🎬 Видео", callback_data=f"child:{kind}:video"),
            InlineKeyboardButton(text="🔵 Кружок", callback_data=f"child:{kind}:note"),
        ],
        [
            InlineKeyboardButton(text="🔘 Кнопка", callback_data=f"child:{kind}:btn"),
            InlineKeyboardButton(text="🗑 Очистить медиа", callback_data=f"child:{kind}:clear_media"),
        ],
        [
            InlineKeyboardButton(text="👁 Предпросмотр", callback_data=f"child:{kind}:preview"),
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="child:back")],
    ])


async def _render_editor(cb_or_msg, kind: str, tenant_id: int):
    g = await get_greeting(tenant_id, kind)
    lines = [("👋 Приветствие" if kind == "hello" else "🧹 Прощание"), ""]
    if g and g.get("text"):
        lines.append(f"Текст: {g['text'][:300] + ('…' if len(g['text'])>300 else '')}")
    else:
        lines.append("Текст: — не задан —")
    media = []
    if g and g.get("photo_file_id"): media.append("фото")
    if g and g.get("video_file_id"): media.append("видео")
    if g and g.get("video_note_file_id"): media.append("кружок")
    lines.append("Медиа: " + (", ".join(media) if media else "—"))
    if g and g.get("button_text"):
        mode = g.get("button_kind", "start")
        if mode == "url":
            lines.append(f"Кнопка: «{g['button_text']}» → URL")
        else:
            lines.append(f"Кнопка: «{g['button_text']}» → START + автоудаление")
    else:
        lines.append("Кнопка: — нет —")

    text = "\n".join(lines)
    kb = _editor_kb(kind)
    if isinstance(cb_or_msg, CallbackQuery):
        await cb_or_msg.message.edit_text(text, reply_markup=kb)
        await cb_or_msg.answer()
    else:
        await cb_or_msg.answer(text, reply_markup=kb)


@router.callback_query(F.data.in_({"child:hello", "child:bye"}))
async def greet_open(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    kind = "hello" if cb.data.endswith("hello") else "bye"
    await _render_editor(cb, kind, tenant["id"])


# --- Текст
@router.callback_query(F.data.func(lambda v: v in {"child:hello:text", "child:bye:text"}))
async def greet_edit_text_start(cb: CallbackQuery, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    kind = "hello" if ":hello:" in cb.data else "bye"
    await state.update_data(kind=kind)
    await state.set_state(GreetSG.wait_text)
    await cb.message.edit_text("Отправь текст (HTML поддерживается).")
    await cb.answer()

@router.message(GreetSG.wait_text)
async def greet_edit_text_save(msg: Message, state: FSMContext, **data):
    tenant = data.get("tenant")
    d = await state.get_data()
    kind = d.get("kind", "hello")
    await set_text(tenant["id"], kind, msg.html_text or msg.text or "")
    await state.clear()
    await _render_editor(msg, kind, tenant["id"])


# --- Фото
@router.callback_query(F.data.func(lambda v: v in {"child:hello:photo", "child:bye:photo"}))
async def greet_edit_photo_start(cb: CallbackQuery, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    kind = "hello" if ":hello:" in cb.data else "bye"
    await state.update_data(kind=kind)
    await state.set_state(GreetSG.wait_photo)
    await cb.message.edit_text("Пришли фото (как фото, не как файл).")
    await cb.answer()

@router.message(GreetSG.wait_photo, F.photo)
async def greet_edit_photo_save(msg: Message, state: FSMContext, **data):
    tenant = data.get("tenant")
    d = await state.get_data()
    kind = d.get("kind", "hello")
    file_id = msg.photo[-1].file_id
    await set_photo(tenant["id"], kind, file_id)
    await state.clear()
    await _render_editor(msg, kind, tenant["id"])

@router.message(GreetSG.wait_photo)
async def greet_edit_photo_bad(msg: Message, **_):
    await msg.answer("Это не похоже на фото. Пришли изображение.")


# --- Видео
@router.callback_query(F.data.func(lambda v: v in {"child:hello:video", "child:bye:video"}))
async def greet_edit_video_start(cb: CallbackQuery, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    kind = "hello" if ":hello:" in cb.data else "bye"
    await state.update_data(kind=kind)
    await state.set_state(GreetSG.wait_video)
    await cb.message.edit_text("Пришли видео (как видео, не как файл).")
    await cb.answer()

@router.message(GreetSG.wait_video, F.video)
async def greet_edit_video_save(msg: Message, state: FSMContext, **data):
    tenant = data.get("tenant")
    d = await state.get_data()
    kind = d.get("kind", "hello")
    file_id = msg.video.file_id
    await set_video(tenant["id"], kind, file_id)
    await state.clear()
    await _render_editor(msg, kind, tenant["id"])

@router.message(GreetSG.wait_video)
async def greet_edit_video_bad(msg: Message, **_):
    await msg.answer("Это не похоже на видео. Пришли видеоролик.")


# --- Кружок (video_note)
@router.callback_query(F.data.func(lambda v: v in {"child:hello:note", "child:bye:note"}))
async def greet_edit_note_start(cb: CallbackQuery, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    kind = "hello" if ":hello:" in cb.data else "bye"
    await state.update_data(kind=kind)
    await state.set_state(GreetSG.wait_note)
    await cb.message.edit_text("Пришли кружок (video note).")
    await cb.answer()

@router.message(GreetSG.wait_note, F.video_note)
async def greet_edit_note_save(msg: Message, state: FSMContext, **data):
    tenant = data.get("tenant")
    d = await state.get_data()
    kind = d.get("kind", "hello")
    file_id = msg.video_note.file_id
    await set_video_note(tenant["id"], kind, file_id)
    await state.clear()
    await _render_editor(msg, kind, tenant["id"])

@router.message(GreetSG.wait_note)
async def greet_edit_note_bad(msg: Message, **_):
    await msg.answer("Это не похоже на кружок. Пришли video note.")


# --- Очистить медиа
@router.callback_query(F.data.func(lambda v: v in {"child:hello:clear_media", "child:bye:clear_media"}))
async def greet_clear_media(cb: CallbackQuery, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    kind = "hello" if ":hello:" in cb.data else "bye"
    await clear_media(tenant["id"], kind)
    await _render_editor(cb, kind, tenant["id"])


# --- Кнопка
@router.callback_query(F.data.func(lambda v: v in {"child:hello:btn", "child:bye:btn"}))
async def greet_btn_start(cb: CallbackQuery, state: FSMContext, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    kind = "hello" if ":hello:" in cb.data else "bye"
    await state.update_data(kind=kind)
    await state.set_state(GreetSG.wait_btn_text)
    await cb.message.edit_text("Введи текст кнопки (или /cancel).")
    await cb.answer()

@router.message(GreetSG.wait_btn_text)
async def greet_btn_text(msg: Message, state: FSMContext, **data):
    await state.update_data(btn_text=(msg.text or "").strip())
    await state.set_state(GreetSG.wait_btn_mode)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Запуск (/start) + автоудаление", callback_data="child:btnmode:start")],
        [InlineKeyboardButton(text="Открыть URL", callback_data="child:btnmode:url")],
    ])
    await msg.answer("Выбери режим кнопки:", reply_markup=kb)

@router.callback_query(F.data.in_(["child:btnmode:start", "child:btnmode:url"]))
async def greet_btn_mode(cb: CallbackQuery, state: FSMContext, **data):
    tenant = data.get("tenant")
    d = await state.get_data()
    kind = d.get("kind", "hello")
    text = d.get("btn_text", "Перейти")

    if cb.data.endswith(":start"):
        await set_button_start(tenant["id"], kind, text)
        await state.clear()
        await _render_editor(cb, kind, tenant["id"])
    else:
        await state.set_state(GreetSG.wait_btn_url)
        await cb.message.edit_text("Пришли URL (https://…)")
        await cb.answer()

@router.message(GreetSG.wait_btn_url)
async def greet_btn_url(msg: Message, state: FSMContext, **data):
    tenant = data.get("tenant")
    d = await state.get_data()
    kind = d.get("kind", "hello")
    text = d.get("btn_text", "Открыть")
    url = (msg.text or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return await msg.answer("Нужен корректный URL, начинающийся с http/https.")
    await set_button_url(tenant["id"], kind, text, url)
    await state.clear()
    await _render_editor(msg, kind, tenant["id"])

# ========= Предпросмотр =========
def _build_btn_markup(g) -> InlineKeyboardMarkup | None:
    if not g or not g.get("button_text"):
        return None
    if g.get("button_kind", "start") == "url":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=g["button_text"], url=g.get("button_url") or "https://t.me")]
        ])
    else:
        # кнопка, которая "как /start" + удаляет сообщение
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=g["button_text"], callback_data="user:start_and_delete")]
        ])

async def _send_greeting_like(bot: Bot, user_id: int, g) -> None:
    if not g:
        return
    kb = _build_btn_markup(g)
    text = g.get("text") or ""

    if g.get("photo_file_id"):
        await bot.send_photo(user_id, g["photo_file_id"], caption=text, parse_mode="HTML",
                             disable_web_page_preview=True, reply_markup=kb)
    elif g.get("video_file_id"):
        await bot.send_video(user_id, g["video_file_id"], caption=text, parse_mode="HTML",
                             disable_web_page_preview=True, reply_markup=kb)
    elif g.get("video_note_file_id"):
        # у кружка нет caption – отправим два сообщения
        await bot.send_video_note(user_id, g["video_note_file_id"])
        if text or kb:
            await bot.send_message(user_id, text or " ", parse_mode="HTML",
                                   disable_web_page_preview=True, reply_markup=kb)
    else:
        await bot.send_message(user_id, text or " ", parse_mode="HTML",
                               disable_web_page_preview=True, reply_markup=kb)

@router.callback_query(F.data.func(lambda v: v in {"child:hello:preview", "child:bye:preview"}))
async def greet_preview(cb: CallbackQuery, bot: Bot, **data):
    tenant = data.get("tenant")
    if not tenant or cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer("Нет доступа", show_alert=True)
    kind = "hello" if ":hello:" in cb.data else "bye"
    g = await get_greeting(tenant["id"], kind)
    await _send_greeting_like(bot, cb.from_user.id, g)
    await cb.answer("Отправил предпросмотр в ЛС.")


# ========= Пользовательская кнопка «/start + удалить» =========
@router.callback_query(F.data == "user:start_and_delete")
async def user_start_and_delete(cb: CallbackQuery, bot: Bot):
    # просто удалить сообщение и, например, ответить «готово» (по желанию)
    try:
        await bot.delete_message(cb.message.chat.id, cb.message.message_id)
    except Exception:
        pass
    await cb.answer("Готово ✅", show_alert=False)


# ========= Автопринятие заявок + ЛС приветствие =========
@router.chat_join_request()
async def on_join_request(event, bot: Bot, **data):
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
    try:
        await _send_greeting_like(bot, user_id, g)
    except Exception:
        pass  # юзер не открыл ДМ или заблокировал


# ========= Прощание в ЛС при выходе =========
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
        user_id = evt.from_user.id if evt.from_user else None
        if not user_id:
            return
        g = await get_greeting(tenant["id"], "bye")
        try:
            await _send_greeting_like(bot, user_id, g)
        except Exception:
            pass

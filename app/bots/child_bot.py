from __future__ import annotations

import asyncio
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, ChatJoinRequest, ChatMemberUpdated,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.exceptions import TelegramForbiddenError

from app.bots.common import (
    child_admin_kb, channels_list_kb,
    greet_editor_kb, greet_button_kb,
)
from app.services.channels_simple import add_channel_by_id, list_channels, delete_channel
from app.services.greetings_simple import (
    get_greeting, set_text, set_photo, set_video, set_video_note,
    clear_media, set_button_start, set_button_url, clear_button,
)

router = Router()

# ------- helpers -------

async def _send_greeting_dm(bot: Bot, user_id: int, tenant_id: int, kind: str) -> Optional[int]:
    g = await get_greeting(tenant_id, kind)
    if not g:
        return None

    text = g.get("text") or ("Добро пожаловать!" if kind == "hello" else "До встречи!")
    kb: Optional[InlineKeyboardMarkup] = None

    if g.get("button_text"):
        if (g.get("button_kind") or "start") == "start":
            me = await bot.get_me()
            deep = f"https://t.me/{me.username}?start=t{tenant_id}"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=g["button_text"], url=deep)]
            ])
        else:
            url = g.get("button_url") or "https://t.me"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=g["button_text"], url=url)]
            ])

    try:
        if g.get("photo_file_id"):
            m = await bot.send_photo(user_id, g["photo_file_id"], caption=text, reply_markup=kb)
            return m.message_id
        if g.get("video_note_file_id"):
            m = await bot.send_video_note(user_id, g["video_note_file_id"])
            await bot.send_message(user_id, text, reply_markup=kb)
            return m.message_id
        if g.get("video_file_id"):
            m = await bot.send_video(user_id, g["video_file_id"], caption=text, reply_markup=kb)
            return m.message_id
        m = await bot.send_message(user_id, text, reply_markup=kb)
        return m.message_id
    except TelegramForbiddenError:
        return None


async def _render_greet_editor(cb: CallbackQuery, tenant_id: int, kind: str):
    g = await get_greeting(tenant_id, kind)
    title = "👋 Приветствие" if kind == "hello" else "🧹 Прощание"
    lines = [title, ""]
    if g:
        lines.append(f"Текст: {g.get('text') or '—'}")
        media = (
            "фото" if g.get("photo_file_id") else
            "видео" if g.get("video_file_id") else
            "кружок" if g.get("video_note_file_id") else "—"
        )
        lines.append(f"Медиа: {media}")
        if g.get("button_text"):
            kind_txt = "START + авт.удаление" if (g.get("button_kind") or "start") == "start" else "URL"
            lines.append(f"Кнопка: «{g['button_text']}» → {kind_txt}")
    else:
        lines.append("Пока пусто. Нажми «Текст»/«Фото» и т.д.")
    await cb.message.edit_text("\n".join(lines), reply_markup=greet_editor_kb(kind))


# ------- /admin -------

@router.message(Command("admin"))
async def admin_root(msg: Message, tenant: dict):
    if msg.from_user.id != tenant["owner_user_id"]:
        return await msg.answer("Доступ только владельцу.")
    await msg.answer("Админ меню", reply_markup=child_admin_kb())


@router.callback_query(F.data == "child:back")
async def admin_back(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    await cb.message.edit_text("Админ меню", reply_markup=child_admin_kb())
    await cb.answer()


# ------- Чаты/каналы -------

@router.callback_query(F.data == "child:chats")
async def chats_open(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    items = await list_channels(tenant["id"])
    await cb.message.edit_text(
        "📣 Чаты/Каналы\nДобавь бота админом в канале/чате.\nВременно можно привязать по ID: отправь в бота `+chat <ID>`.",
        reply_markup=channels_list_kb(items),
        parse_mode="Markdown",
    )
    await cb.answer()


@router.message(F.text.regexp(r"^\+chat\s-?\d+$"))
async def chats_add_cmd(msg: Message, tenant: dict):
    if msg.from_user.id != tenant["owner_user_id"]:
        return
    chat_id = int(msg.text.split()[1])
    await add_channel_by_id(tenant["id"], chat_id, title=None)
    await msg.answer("Готово. Чат/канал добавлен. Дайте боту админ-права в канале/чате.")


@router.callback_query(F.data.startswith("child:chdel:"))
async def chats_del(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    ch_id = int(cb.data.split(":")[-1])
    await delete_channel(tenant["id"], ch_id)
    items = await list_channels(tenant["id"])
    await cb.message.edit_text("📣 Чаты/Каналы", reply_markup=channels_list_kb(items))
    await cb.answer("Удалено")


# ------- Приветствие/прощание: вход в редактор -------

@router.callback_query(F.data.in_({"child:hello", "child:bye"}))
async def greet_root(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    kind = "hello" if cb.data == "child:hello" else "bye"
    await _render_greet_editor(cb, tenant["id"], kind)
    await cb.answer()


# ------- Предпросмотр -------

@router.callback_query(F.data.startswith("child:greet:preview:"))
async def greet_preview(cb: CallbackQuery, tenant: dict, bot: Bot):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    kind = cb.data.split(":")[-1]
    mid = await _send_greeting_dm(bot, cb.from_user.id, tenant["id"], kind)
    if mid is None:
        return await cb.answer("Не могу написать в ЛС: пользователь не нажимал START у этого бота.", show_alert=True)
    async def _autodel():
        await asyncio.sleep(10)
        try:
            await bot.delete_message(cb.from_user.id, mid)
        except Exception:
            pass
    asyncio.create_task(_autodel())
    await cb.answer("Отправил превью в ЛС (удалю через ~10 сек).")


# ------- Редактирование текста -------

@router.callback_query(F.data.startswith("child:greet:edit:text:"))
async def greet_edit_text(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    kind = cb.data.split(":")[-1]
    await cb.message.edit_text(
        "Отправь новый текст (или `-` чтобы очистить).",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Отмена", callback_data=f"child:greet:open:{kind}")]
        ]),
        parse_mode="Markdown",
    )

    @router.message(F.chat.id == cb.message.chat.id)
    async def _catch(msg: Message):
        new_text = None if (msg.text or "").strip() == "-" else msg.text
        await set_text(tenant["id"], kind, new_text or "")
        await msg.answer("Сохранено.")
        await _render_greet_editor(cb, tenant["id"], kind)
        router.message.handlers.pop()  # один раз


# ------- Медиа -------

@router.callback_query(F.data.startswith("child:greet:set:photo:"))
async def greet_set_photo(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    kind = cb.data.split(":")[-1]
    await cb.message.edit_text(
        "Пришли фото (или `-` чтобы убрать).",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Отмена", callback_data=f"child:greet:open:{kind}")]
        ]),
    )

    @router.message(F.photo)
    async def _cap(msg: Message):
        await set_photo(tenant["id"], kind, msg.photo[-1].file_id)
        await msg.answer("Фото сохранено.")
        await _render_greet_editor(cb, tenant["id"], kind)
        router.message.handlers.pop()

    @router.message(F.text == "-")
    async def _clr(msg: Message):
        await clear_media(tenant["id"], kind)
        await msg.answer("Медиа очищено.")
        await _render_greet_editor(cb, tenant["id"], kind)
        router.message.handlers.pop()


@router.callback_query(F.data.startswith("child:greet:set:video:"))
async def greet_set_video(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    kind = cb.data.split(":")[-1]
    await cb.message.edit_text(
        "Пришли видео (или `-` чтобы убрать).",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Отмена", callback_data=f"child:greet:open:{kind}")]
        ]),
    )

    @router.message(F.video)
    async def _cap(msg: Message):
        await set_video(tenant["id"], kind, msg.video.file_id)
        await msg.answer("Видео сохранено.")
        await _render_greet_editor(cb, tenant["id"], kind)
        router.message.handlers.pop()

    @router.message(F.text == "-")
    async def _clr(msg: Message):
        await clear_media(tenant["id"], kind)
        await msg.answer("Медиа очищено.")
        await _render_greet_editor(cb, tenant["id"], kind)
        router.message.handlers.pop()


@router.callback_query(F.data.startswith("child:greet:set:videonote:"))
async def greet_set_vn(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    kind = cb.data.split(":")[-1]
    await cb.message.edit_text(
        "Пришли кружок (или `-` чтобы убрать).",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Отмена", callback_data=f"child:greet:open:{kind}")]
        ]),
    )

    @router.message(F.video_note)
    async def _cap(msg: Message):
        await set_video_note(tenant["id"], kind, msg.video_note.file_id)
        await msg.answer("Кружок сохранён.")
        await _render_greet_editor(cb, tenant["id"], kind)
        router.message.handlers.pop()

    @router.message(F.text == "-")
    async def _clr(msg: Message):
        await clear_media(tenant["id"], kind)
        await msg.answer("Медиа очищено.")
        await _render_greet_editor(cb, tenant["id"], kind)
        router.message.handlers.pop()


@router.callback_query(F.data.startswith("child:greet:clear_media:"))
async def greet_clear_media(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    kind = cb.data.split(":")[-1]
    await clear_media(tenant["id"], kind)
    await _render_greet_editor(cb, tenant["id"], kind)
    await cb.answer("Очищено")


# ------- Кнопка -------

@router.callback_query(F.data.startswith("child:greet:btn:"))
async def greet_btn_root(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    # child:greet:btn:<kind>
    kind = cb.data.split(":")[-1]
    await cb.message.edit_text("Настройки кнопки", reply_markup=greet_button_kb(kind))
    await cb.answer()


@router.callback_query(F.data.startswith("child:greet:btn:set_start:"))
async def greet_btn_start(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    kind = cb.data.split(":")[-1]
    await set_button_start(tenant["id"], kind, "ОСТАВАТЬСЯ НА СВЯЗИ")
    await _render_greet_editor(cb, tenant["id"], kind)
    await cb.answer("Кнопка START задана")


@router.callback_query(F.data.startswith("child:greet:btn:set_url:"))
async def greet_btn_url(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    kind = cb.data.split(":")[-1]
    await set_button_url(tenant["id"], kind, "Открыть сайт", "https://t.me")
    await _render_greet_editor(cb, tenant["id"], kind)
    await cb.answer("Кнопка URL задана")


@router.callback_query(F.data.startswith("child:greet:btn:clear:"))
async def greet_btn_clear(cb: CallbackQuery, tenant: dict):
    if cb.from_user.id != tenant["owner_user_id"]:
        return await cb.answer()
    kind = cb.data.split(":")[-1]
    await clear_button(tenant["id"], kind)
    await _render_greet_editor(cb, tenant["id"], kind)
    await cb.answer("Кнопка убрана")


# ------- Авто-аппрув + DM -------

@router.chat_join_request()
async def on_join_request(evt: ChatJoinRequest, bot: Bot, tenant: dict):
    try:
        await bot.approve_chat_join_request(evt.chat.id, evt.from_user.id)
    except Exception:
        pass
    try:
        await _send_greeting_dm(bot, evt.from_user.id, tenant["id"], "hello")
    except Exception:
        pass


@router.chat_member()
async def on_chat_member(evt: ChatMemberUpdated, bot: Bot, tenant: dict):
    try:
        old = getattr(evt, "old_chat_member", None)
        new = getattr(evt, "new_chat_member", None)
        if old and new and getattr(old, "status", None) == "member" and getattr(new, "status", None) in {"left", "kicked"}:
            await _send_greeting_dm(bot, evt.from_user.id, tenant["id"], "bye")
    except Exception:
        pass

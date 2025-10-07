from __future__ import annotations

import asyncio
from typing import Optional, Tuple, Dict

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, ChatJoinRequest, ChatMemberUpdated,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.enums import ParseMode

from app.bots.common import (
    child_admin_kb, child_settings_kb,
)
from app.services.greetings_simple import get_greeting, save_greeting  # у тебя уже есть этот модуль
from app.services.settings_simple import get_collect_requests, toggle_collect_requests
from app.services.pending import add_request, list_new, mark_approved, mark_failed

router = Router()

# ====== helpers ======

def _tenant_id_from_bot(bot: Bot) -> int:
    # middleware кладёт сюда словарь: {"id": t.id, "owner_user_id": ...}
    t = getattr(bot, "_tenant", None)
    if not t or "id" not in t:
        raise RuntimeError("Tenant context is missing. Check TenantContext middleware.")
    return int(t["id"])

async def _send_dm_greeting(bot: Bot, user_id: int, tenant_id: int, kind: str = "hello") -> bool:
    """
    Пытаемся отправить ЛС с приветствием/прощанием.
    Возвращаем True при успехе, False если нельзя (403 и т.п.) или нет настроек.
    НИЧЕГО в чаты/каналы не отправляем.
    """
    g = await get_greeting(tenant_id, kind)
    if not g:
        return False

    text = g.get("text") or ""
    parse_mode = g.get("parse_mode") or None
    button_text = g.get("button_text")
    button_url = g.get("button_url")
    disable_preview = bool(g.get("disable_preview") or False)

    kb: Optional[InlineKeyboardMarkup] = None
    if button_text and button_url:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, url=button_url)]
        ])

    try:
        # Медиа приоритет: фото > видео > кружок > просто текст
        if g.get("photo_file_id"):
            await bot.send_photo(
                chat_id=user_id,
                photo=g["photo_file_id"],
                caption=text or None,
                parse_mode=parse_mode or ParseMode.MARKDOWN,
                reply_markup=kb,
                has_spoiler=False,
            )
            return True
        if g.get("video_file_id"):
            await bot.send_video(
                chat_id=user_id,
                video=g["video_file_id"],
                caption=text or None,
                parse_mode=parse_mode or ParseMode.MARKDOWN,
                reply_markup=kb,
                supports_streaming=True
            )
            return True
        if g.get("video_note_file_id"):
            await bot.send_video_note(
                chat_id=user_id,
                video_note=g["video_note_file_id"],
                reply_markup=kb,
            )
            if text:
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode=parse_mode or ParseMode.MARKDOWN,
                    reply_markup=kb,
                    disable_web_page_preview=disable_preview,
                )
            return True

        # Просто текст
        if text:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=parse_mode or ParseMode.MARKDOWN,
                reply_markup=kb,
                disable_web_page_preview=disable_preview,
            )
            return True

        return False

    except TelegramForbiddenError:
        # Пользователь не открывал ЛС/заблокировал — молчим
        return False
    except TelegramBadRequest:
        # Например, неверный parse_mode/контент — считаем как не доставлено, но не ломаем поток
        return False


# ====== /admin и главное меню ======

@router.message(Command("admin"))
async def child_admin_menu(msg: Message, bot: Bot):
    tenant_id = _tenant_id_from_bot(bot)
    collect = await get_collect_requests(tenant_id)
    await msg.answer(
        "Админ-меню\n\n"
        "Здесь вы настраиваете бота: приветствие, прощание и управление заявками.\n"
        "Бот НИКОГДА не пишет в чаты — только в ЛС (если возможно).",
        reply_markup=child_admin_kb(collect_enabled=collect)
    )


@router.callback_query(F.data == "child:home")
async def cb_child_home(cb: CallbackQuery, bot: Bot):
    tenant_id = _tenant_id_from_bot(bot)
    collect = await get_collect_requests(tenant_id)
    await cb.message.edit_text(
        "Админ-меню",
        reply_markup=child_admin_kb(collect_enabled=collect)
    )
    await cb.answer()


# ====== Настройки ======

@router.callback_query(F.data == "child:settings")
async def cb_child_settings(cb: CallbackQuery, bot: Bot):
    tenant_id = _tenant_id_from_bot(bot)
    collect = await get_collect_requests(tenant_id)
    await cb.message.edit_text(
        "⚙️ Настройки\n\n"
        "• Копить заявки — если включено, новые заявки НЕ апрувятся сразу, а попадают в очередь.\n"
        "• Собрать заявки — апрувит все накопленные заявки и тихо пробует отправить приветствие в ЛС.",
        reply_markup=child_settings_kb(collect_enabled=collect)
    )
    await cb.answer()


@router.callback_query(F.data == "child:settings:collect_toggle")
async def cb_child_collect_toggle(cb: CallbackQuery, bot: Bot):
    tenant_id = _tenant_id_from_bot(bot)
    new_value = await toggle_collect_requests(tenant_id)
    await cb.message.edit_reply_markup(reply_markup=child_settings_kb(collect_enabled=new_value))
    await cb.answer("Режим обновлён")


@router.callback_query(F.data == "child:settings:collect_run")
async def cb_child_collect_run(cb: CallbackQuery, bot: Bot):
    tenant_id = _tenant_id_from_bot(bot)
    await cb.answer("Запускаю сбор заявок…", show_alert=False)

    rows = await list_new(tenant_id, limit=2000)
    ok, fail = 0, 0

    for r in rows:
        row_id = r["id"]
        chat_id = int(r["chat_id"])
        user_id = int(r["user_id"])

        try:
            await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            # тихо пробуем ЛС
            delivered = await _send_dm_greeting(bot, user_id, tenant_id, kind="hello")
            await mark_approved(row_id, dm_ok=delivered, error=None)
            ok += 1
        except Exception as e:
            await mark_failed(row_id, error=str(e)[:300])
            fail += 1

        # анти-флуд
        await asyncio.sleep(0.15)

    await cb.message.answer(f"Сбор завершён:\n✅ Одобрено: {ok}\n⚠️ Ошибок: {fail}")
    await cb.answer()


# ====== Приветствие/Прощание — редактор (простая заглушка текста) ======
# У тебя уже есть полноценные редакторы, ниже — только "быстрые" заглушки — можно оставить или интегрировать с твоими.

@router.callback_query(F.data.startswith("child:greet:"))
async def cb_child_greet_menu(cb: CallbackQuery, bot: Bot):
    tenant_id = _tenant_id_from_bot(bot)
    kind = "hello" if cb.data.endswith(":hello") else "bye"
    g = await get_greeting(tenant_id, kind)
    title = "👋 Приветствие" if kind == "hello" else "🧹 Прощание"

    lines = [title, ""]
    if g:
        media = (
            "фото" if g.get("photo_file_id") else
            "видео" if g.get("video_file_id") else
            "кружок" if g.get("video_note_file_id") else "—"
        )
        lines.append(f"Текст: {g.get('text') or '—'}")
        lines.append(f"Медиа: {media}")
        if g.get("button_text") and g.get("button_url"):
            lines.append(f"Кнопка: {g['button_text']} → {g['button_url']}")
    else:
        lines.append("Не настроено.")

    lines.append("")
    lines.append("Изменение медиа/кнопок — в расширенном редакторе (будет в следующих шагах).")

    await cb.message.edit_text("\n".join(lines))
    await cb.answer()


# ====== События: заявка на вступление / выход из чата ======

@router.chat_join_request()
async def on_chat_join_request(event: ChatJoinRequest, bot: Bot):
    tenant_id = _tenant_id_from_bot(bot)
    chat_id = int(event.chat.id)
    user_id = int(event.from_user.id)

    # проверяем режим
    collect = await get_collect_requests(tenant_id)

    if collect:
        # копим заявку
        try:
            await add_request(tenant_id=tenant_id, chat_id=chat_id, user_id=user_id)
        except Exception:
            # Не ломаем поток
            pass
        # Ничего больше не делаем (ни ЛС, ни апрува)
        return

    # иначе — автоапрув + тихая попытка ЛС
    try:
        await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
    except Exception:
        # если не получилось — молчим (не пишем в чаты), просто выходим
        return

    # ЛС приветствие — тихая попытка
    await _send_dm_greeting(bot, user_id, tenant_id, kind="hello")


@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated, bot: Bot):
    """
    Отправляем прощание в ЛС, когда пользователь выходит/кикается, если возможно.
    НИЧЕГО в чаты/каналы не отправляем.
    """
    try:
        # Нас интересует уход обычного участника
        if event.old_chat_member and event.new_chat_member:
            old_status = getattr(event.old_chat_member, "status", None)
            new_status = getattr(event.new_chat_member, "status", None)
        else:
            return

        # Был member → стал left/kicked
        if str(old_status) in {"member"} and str(new_status) in {"left", "kicked"}:
            tenant_id = _tenant_id_from_bot(bot)
            user_id = int(event.from_user.id) if event.from_user else None
            # На некоторых типах апдейтов нужный id — в new_chat_member.user.id
            if not user_id and hasattr(event, "new_chat_member") and getattr(event.new_chat_member, "user", None):
                user_id = int(event.new_chat_member.user.id)
            if not user_id:
                return

            # Тихая попытка ЛС-прощания
            await _send_dm_greeting(bot, user_id, tenant_id, kind="bye")

    except Exception:
        # Любые ошибки — молча игнорим (не пишем в чаты)
        return

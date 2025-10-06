from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.settings import ADMIN_IDS
from app.bots.common import ga_main_kb, ga_clients_page_kb, tenant_card_kb
from app.services.membership import is_in_group
from app.services.tenants_simple import (
    get_tenant_by_owner, upsert_tenant, save_bot_username,
    list_tenants, get_tenant, delete_tenant,
)
from app.services.webhooks_child import set_child_webhook

import asyncio

router = Router()

# === /start и приём токена ===

@router.message(Command("start"))
async def start(msg: Message, bot: Bot):
    if await is_in_group(bot, msg.from_user.id):
        await msg.answer(
            "Привет! Если ты в приватке — пришли API-token своего бота "
            "(формат 1234567890:AAAA...). Один владелец → один бот."
        )
    else:
        await msg.answer("Привет! Ты не в приватке. Напиши @toffadds, чтобы узнать условия.")

@router.message(F.text.regexp(r"^\d{9,10}:[A-Za-z0-9_-]{35,}$"))
async def connect_child(msg: Message, bot: Bot):
    uid = msg.from_user.id
    if not await is_in_group(bot, uid):
        return await msg.answer("Ты не в приватке. Напиши @toffadds.")

    # Строго: 1 владелец → 1 бот
    existing = await get_tenant_by_owner(uid)
    if existing:
        user = existing.get("owner_username") or existing.get("owner_user_id")
        buser = existing.get("bot_username") or "—"
        return await msg.answer(
            f"У тебя уже подключён бот @{buser}. Один владелец → один бот.\n"
            f"Если понадобится заменить токен — сделаем отдельной командой."
        )

    token = msg.text.strip()
    tenant_id, secret = await upsert_tenant(uid, msg.from_user.username, token)

    cbot = Bot(token)
    me = await cbot.get_me()
    await save_bot_username(tenant_id, me.username)
    await set_child_webhook(cbot, tenant_id, secret)

    await msg.answer(f"Ваш бот успешно подключён! Перейдите к нему и завершите настройку: @{me.username}")

# === /ga (только админы) ===

@router.message(Command("ga"))
async def ga_root(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.answer("Главный админ", reply_markup=ga_main_kb())

@router.callback_query(F.data == "ga:deploy")
async def ga_deploy(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer()
    await cb.message.answer("Запустил деплой…")
    proc = await asyncio.create_subprocess_shell(
        "/usr/local/bin/multibot_deploy.sh",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    out, _ = await proc.communicate()
    text = out.decode(errors="ignore")[-3500:] or "no output"
    await cb.message.answer(f"Готово.\n```\n{text}\n```", parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data == "ga:restart")
async def ga_restart(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer()
    await cb.message.answer("Рестартую сервис…")
    proc = await asyncio.create_subprocess_shell(
        "systemctl restart multibot && systemctl is-active multibot",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    out, _ = await proc.communicate()
    await cb.message.answer(f"Статус: `{out.decode().strip()}`", parse_mode="Markdown")
    await cb.answer()

@router.callback_query(F.data.startswith("ga:clients:"))
async def ga_clients(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer()
    page = int(cb.data.split(":")[-1])
    page_size = 10
    rows = await list_tenants(page, page_size)
    has_next = len(rows) > page_size
    rows = rows[:page_size]
    text = "Список клиентов:\n" + "\n".join(
        [f"• #{r['id']} @{r.get('bot_username') or '—'} (owner: @{r.get('owner_username') or r['owner_user_id']})  → /tenant_{r['id']}"
         for r in rows] or ["пусто"]
    )
    await cb.message.edit_text(text, reply_markup=ga_clients_page_kb(page, page > 1, has_next))
    await cb.answer()

@router.message(F.text.regexp(r"^/tenant_(\d+)$"))
async def ga_tenant_card(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    tenant_id = int(msg.text.split("_")[-1])
    t = await get_tenant(tenant_id)
    if not t:
        return await msg.answer("Не найден")
    text = (
        f"Тенант #{t['id']}\n"
        f"Владелец: @{t.get('owner_username') or t['owner_user_id']}\n"
        f"Бот: @{t.get('bot_username') or '—'}\n"
        f"Статус: {'Активен' if t.get('is_active') else 'Выключен'}\n"
    )
    await msg.answer(text, reply_markup=tenant_card_kb(t['id']))

@router.callback_query(F.data.startswith("ga:tenant:"))
async def ga_tenant_actions(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer()
    _, _, tid, action = cb.data.split(":")
    tid = int(tid)
    if action == "delete":
        await delete_tenant(tid)
        await cb.message.edit_text("Клиент удалён. Его бот остановлен. Можно подключить нового в GA-боте.")
    await cb.answer()

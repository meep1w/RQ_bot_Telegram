from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message
from app.services.membership import is_in_group
from app.services.tenants_simple import upsert_tenant, save_bot_username
from app.services.webhooks_child import set_child_webhook
from app.settings import ADMIN_IDS
import asyncio

router = Router()

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
    token = msg.text.strip()
    tenant_id, secret = await upsert_tenant(uid, msg.from_user.username, token)

    cbot = Bot(token)
    me = await cbot.get_me()
    await save_bot_username(tenant_id, me.username)
    await set_child_webhook(cbot, tenant_id, secret)

    await msg.answer(f"Ваш бот успешно подключён! Перейдите к нему и завершите настройку: @{me.username}")

@router.message(Command("deploy"))
async def deploy(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.answer("Запустил деплой…")
    proc = await asyncio.create_subprocess_shell(
        "/usr/local/bin/multibot_deploy.sh",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    out, _ = await proc.communicate()
    text = out.decode(errors="ignore")[-3500:] or "no output"
    await msg.answer(f"Готово.\n```\n{text}\n```", parse_mode="Markdown")

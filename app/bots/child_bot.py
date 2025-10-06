from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

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

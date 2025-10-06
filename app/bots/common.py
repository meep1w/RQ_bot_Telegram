from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any
from typing import Optional


def ga_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚙️ Деплой",  callback_data="ga:deploy"),
            InlineKeyboardButton(text="🔁 Рестарт", callback_data="ga:restart"),
        ],
        [InlineKeyboardButton(text="👥 Список клиентов", callback_data="ga:clients:1")],
    ])


def ga_clients_kb(items: List[Dict[str, Any]], page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    # Кнопки-строки со списком клиентов
    for r in items:
        owner_label = f"@{r.get('owner_username') or r['owner_user_id']}"
        rows.append([InlineKeyboardButton(text=owner_label, callback_data=f"ga:tenant:{r['id']}:open:{page}")])

    # Навигация
    nav: list[InlineKeyboardButton] = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="⟵", callback_data=f"ga:clients:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"Стр. {page}", callback_data="noop"))
    if has_next:
        nav.append(InlineKeyboardButton(text="⟶", callback_data=f"ga:clients:{page+1}"))
    rows.append(nav)

    # Назад в меню
    rows.append([InlineKeyboardButton(text="↩︎ В меню", callback_data="ga:menu")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def tenant_card_kb(tenant_id: int, page_back: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить клиента", callback_data=f"ga:tenant:{tenant_id}:delete:{page_back}")],
        [InlineKeyboardButton(text="↩︎ К списку", callback_data=f"ga:clients:{page_back}")],
    ])


# Детский бот — админ-меню
def child_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📣 Чаты/Каналы", callback_data="child:chats")],
        [
            InlineKeyboardButton(text="👋 Приветствие", callback_data="child:hello"),
            InlineKeyboardButton(text="🧹 Прощание",   callback_data="child:bye"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="child:settings"),
            InlineKeyboardButton(text="📰 Рассылка",  callback_data="child:broadcast"),
        ],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="child:stats")],
    ])


def channels_list_kb(items: list[dict], page: int = 1) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if items:
        for r in items:
            label = f"{r.get('title') or r['chat_id']}"
            rows.append([InlineKeyboardButton(text=label, callback_data=f"child:ch:{r['id']}")])
            rows.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"child:chdel:{r['id']}")])
    else:
        rows.append([InlineKeyboardButton(text="Нет подключённых", callback_data="noop")])

    rows.append([InlineKeyboardButton(text="🔗 Подключить чат", callback_data="child:chadd")])
    rows.append([InlineKeyboardButton(text="↩︎ В меню", callback_data="child:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

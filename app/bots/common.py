from typing import Any, Dict, List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


# ====== GA (главный бот) ======

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
    for t in items:
        label = f"@{t.get('owner_username') or t['owner_user_id']}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"ga:tenant:{t['id']}")])

    pager: list[InlineKeyboardButton] = []
    if has_prev:
        pager.append(InlineKeyboardButton(text="⬅️", callback_data=f"ga:clients:{page-1}"))
    pager.append(InlineKeyboardButton(text=f"Стр. {page}", callback_data="noop"))
    if has_next:
        pager.append(InlineKeyboardButton(text="➡️", callback_data=f"ga:clients:{page+1}"))
    rows.append(pager or [InlineKeyboardButton(text="—", callback_data="noop")])

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="ga:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tenant_card_kb(tenant_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить клиента", callback_data=f"ga:tenantdel:{tenant_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="ga:clients:1")],
    ])


# ====== CHILD (бот клиента) ======

def child_admin_kb(collect_enabled: bool) -> InlineKeyboardMarkup:
    flag = "✅" if collect_enabled else "❌"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Приветствие", callback_data="child:greet:hello"),
            InlineKeyboardButton(text="🧹 Прощание",    callback_data="child:greet:bye"),
        ],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="child:settings")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="child:stats")],
    ])


def child_settings_kb(collect_enabled: bool) -> InlineKeyboardMarkup:
    flag = "✅" if collect_enabled else "❌"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{flag} Копить заявки", callback_data="child:settings:collect_toggle")],
        [InlineKeyboardButton(text="🧺 Собрать заявки", callback_data="child:settings:collect_run")],
        [InlineKeyboardButton(text="⬅️ Вернуться в меню", callback_data="child:home")],
    ])


def channels_list_kb(items: List[Dict[str, Any]], page: int = 1) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if items:
        for r in items:
            label = f"{r.get('title') or r['chat_id']}"
            rows.append([InlineKeyboardButton(text=label, callback_data=f"child:ch:{r['id']}")])
            rows.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"child:chdel:{r['id']}")])
    else:
        rows.append([InlineKeyboardButton(text="Нет подключённых", callback_data="noop")])

    rows.append([InlineKeyboardButton(text="🔗 Подключить чат", callback_data="child:chadd")])
    rows.append([InlineKeyboardButton(text="⬅️ Вернуться в меню", callback_data="child:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

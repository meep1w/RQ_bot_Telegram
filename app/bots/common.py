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

    # Строки-кнопки со списком клиентов
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


# ====== Детский бот ======

def child_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📣 Чаты/Каналы", callback_data="child:chats")],
        [
            InlineKeyboardButton(text="👋 Приветствие", callback_data="child:greet:open:hello"),
            InlineKeyboardButton(text="🧹 Прощание",   callback_data="child:greet:open:bye"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="child:settings"),
            InlineKeyboardButton(text="📰 Рассылка",  callback_data="child:broadcast"),
        ],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="child:stats")],
    ])


def greet_editor_kb(kind: str) -> InlineKeyboardMarkup:
    """
    kind: 'hello' | 'bye'
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Текст", callback_data=f"child:greet:edit:text:{kind}"),
            InlineKeyboardButton(text="🖼️ Фото", callback_data=f"child:greet:set:photo:{kind}"),
        ],
        [
            InlineKeyboardButton(text="🎬 Видео", callback_data=f"child:greet:set:video:{kind}"),
            InlineKeyboardButton(text="🔵 Кружок", callback_data=f"child:greet:set:videonote:{kind}"),
        ],
        [
            InlineKeyboardButton(text="🔘 Кнопка", callback_data=f"child:greet:btn:{kind}"),
            InlineKeyboardButton(text="🧽 Очистить медиа", callback_data=f"child:greet:clear_media:{kind}"),
        ],
        [InlineKeyboardButton(text="👁️ Предпросмотр", callback_data=f"child:greet:preview:{kind}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="child:back")],
    ])


def greet_button_kb(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Deep-link START", callback_data=f"child:greet:btn:set_start:{kind}"),
            InlineKeyboardButton(text="🔗 URL",             callback_data=f"child:greet:btn:set_url:{kind}"),
        ],
        [InlineKeyboardButton(text="❌ Убрать кнопку", callback_data=f"child:greet:btn:clear:{kind}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"child:greet:open:{kind}")],
    ])


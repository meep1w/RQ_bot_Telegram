from typing import Any, Dict, List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ====== GA ======

def ga_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Деплой", callback_data="ga:deploy"),
         InlineKeyboardButton(text="🔁 Рестарт", callback_data="ga:restart")],
        [InlineKeyboardButton(text="👥 Список клиентов", callback_data="ga:clients:1")],
    ])

def ga_clients_kb(items: List[Dict[str, Any]], page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for r in items:
        owner = f"@{r.get('owner_username') or r['owner_user_id']}"
        rows.append([InlineKeyboardButton(text=owner, callback_data=f"ga:tenant:{r['id']}:open:{page}")])
    nav: list[InlineKeyboardButton] = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="⟵", callback_data=f"ga:clients:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"Стр. {page}", callback_data="noop"))
    if has_next:
        nav.append(InlineKeyboardButton(text="⟶", callback_data=f"ga:clients:{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton(text="↩︎ В меню", callback_data="ga:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def tenant_card_kb(tenant_id: int, page_back: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить клиента", callback_data=f"ga:tenant:{tenant_id}:delete:{page_back}")],
        [InlineKeyboardButton(text="↩︎ К списку", callback_data=f"ga:clients:{page_back}")],
    ])

# ====== CHILD ======

def child_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📣 Чаты/Каналы", callback_data="child:chats")],
        [InlineKeyboardButton(text="👋 Приветствие", callback_data="child:hello"),
         InlineKeyboardButton(text="🧹 Прощание", callback_data="child:bye")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="child:settings"),
         InlineKeyboardButton(text="📰 Рассылка", callback_data="child:broadcast")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="child:stats")],
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
    rows.append([InlineKeyboardButton(text="↩︎ В меню", callback_data="child:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ——— Greeting editor ———

def greet_editor_kb(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Текст", callback_data=f"child:greet:edit:text:{kind}")],
        [InlineKeyboardButton(text="🖼 Фото", callback_data=f"child:greet:set:photo:{kind}"),
         InlineKeyboardButton(text="🎬 Видео", callback_data=f"child:greet:set:video:{kind}")],
        [InlineKeyboardButton(text="🥎 Кружок", callback_data=f"child:greet:set:videonote:{kind}"),
         InlineKeyboardButton(text="🧽 Очистить медиа", callback_data=f"child:greet:clear_media:{kind}")],
        [InlineKeyboardButton(text="🔘 Кнопка", callback_data=f"child:greet:btn:{kind}")],
        [InlineKeyboardButton(text="👁 Предпросмотр", callback_data=f"child:greet:preview:{kind}")],
        [InlineKeyboardButton(text="↩︎ Назад", callback_data="child:back")],
    ])

def greet_button_kb(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ START + авт.удаление", callback_data=f"child:greet:btn:set_start:{kind}")],
        [InlineKeyboardButton(text="🔗 Обычная ссылка (URL)", callback_data=f"child:greet:btn:set_url:{kind}")],
        [InlineKeyboardButton(text="🧽 Убрать кнопку", callback_data=f"child:greet:btn:clear:{kind}")],
        [InlineKeyboardButton(text="↩︎ Назад", callback_data=f"child:greet:open:{kind}")],
    ])

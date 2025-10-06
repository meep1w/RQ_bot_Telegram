from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def ga_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Деплой", callback_data="ga:deploy"),
         InlineKeyboardButton(text="🔁 Рестарт", callback_data="ga:restart")],
        [InlineKeyboardButton(text="👥 Список клиентов", callback_data="ga:clients:1")],
    ])

def ga_clients_page_kb(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    row = []
    if has_prev:
        row.append(InlineKeyboardButton(text="⟵", callback_data=f"ga:clients:{page-1}"))
    row.append(InlineKeyboardButton(text=f"Стр. {page}", callback_data="noop"))
    if has_next:
        row.append(InlineKeyboardButton(text="⟶", callback_data=f"ga:clients:{page+1}"))
    return InlineKeyboardMarkup(inline_keyboard=[row])

def tenant_card_kb(tenant_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить клиента", callback_data=f"ga:tenant:{tenant_id}:delete")],
    ])

def child_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📣 Чаты/Каналы", callback_data="child:chats")],
        [InlineKeyboardButton(text="👋 Приветствие", callback_data="child:hello"),
         InlineKeyboardButton(text="🧹 Прощание",   callback_data="child:bye")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="child:settings"),
         InlineKeyboardButton(text="📰 Рассылка",  callback_data="child:broadcast")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="child:stats")],
    ])

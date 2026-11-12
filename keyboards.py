from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from config import ADMIN_ID

def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Asosiy pastki klaviatura (Adminga maxsus Admin Panel tugmasi bilan)."""
    buttons = [
        [
            KeyboardButton(text="📊 Xotira holati"),
            KeyboardButton(text="🗑 Xotirani tozalash")
        ],
        [
            KeyboardButton(text="ℹ️ Bot haqida")
        ]
    ]
    
    # Agar foydalanuvchi Admin bo'lsa, maxsus tugma qo'shiladi
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="👑 Admin Panel")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        persistent=True
    )

def get_clear_confirm_keyboard() -> InlineKeyboardMarkup:
    """Xotirani tozalashni tasdiqlash inline tugmasi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, tozalansin", callback_data="confirm_clear_memory"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_clear_memory")
            ]
        ]
    )

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Admin boshqaruv paneli menyusi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Umumiy statistika", callback_data="admin_stats"),
                InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton(text="💬 Suhbatlar monitoringi", callback_data="admin_chats_0")
            ],
            [
                InlineKeyboardButton(text="📢 Xabar tarqatish (Broadcast)", callback_data="admin_broadcast"),
                InlineKeyboardButton(text="❌ Yopish", callback_data="admin_close")
            ]
        ]
    )

def get_chat_logs_keyboard(offset: int, has_more: bool) -> InlineKeyboardMarkup:
    """Suhbatlar tarixini sahifalab ko'rish inline tugmalari."""
    nav_buttons = []
    if offset > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_chats_{offset - 5}"))
    nav_buttons.append(InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"admin_chats_{offset}"))
    if has_more:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_chats_{offset + 5}"))

    return InlineKeyboardMarkup(
        inline_keyboard=[
            nav_buttons,
            [InlineKeyboardButton(text="🔙 Admin panelga qaytish", callback_data="admin_back")]
        ]
    )

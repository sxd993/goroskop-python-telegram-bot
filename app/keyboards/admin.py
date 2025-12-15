from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import MONTH_NAMES_RU, SIGNS_RU


ADMIN_ADD_FORECAST_CALLBACK = "admin:add_forecast"
ADMIN_DELETE_FORECAST_CALLBACK = "admin:delete_forecast"
ADMIN_STATS_CALLBACK = "admin:stats"
ADMIN_BACK_MENU_CALLBACK = "admin-back:menu"


def build_admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить прогноз", callback_data=ADMIN_ADD_FORECAST_CALLBACK)
    builder.button(text="Удалить прогноз", callback_data=ADMIN_DELETE_FORECAST_CALLBACK)
    builder.button(text="Статистика продаж", callback_data=ADMIN_STATS_CALLBACK)
    builder.adjust(1)
    return builder.as_markup()


def build_admin_type_keyboard(include_back: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Годовой", callback_data="admin-type:year")
    builder.button(text="Месячный", callback_data="admin-type:month")
    builder.adjust(2)
    if include_back:
        builder.button(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)
        builder.adjust(2)
    return builder.as_markup()


def build_admin_months_keyboard(include_back: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for month, name in MONTH_NAMES_RU.items():
        builder.button(text=name, callback_data=f"admin-month:{month:02d}")
    builder.adjust(3)
    if include_back:
        builder.button(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)
        builder.adjust(3)
    return builder.as_markup()


def build_admin_signs_keyboard(include_back: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sign, name in SIGNS_RU.items():
        builder.button(text=name, callback_data=f"admin-sign:{sign}")
    builder.adjust(3)
    if include_back:
        builder.button(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)
        builder.adjust(3)
    return builder.as_markup()

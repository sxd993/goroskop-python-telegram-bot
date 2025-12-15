from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import MONTH_NAMES_RU, SIGNS_RU


ADMIN_ADD_FORECAST_CALLBACK = "admin:add_forecast"


def build_admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить прогноз", callback_data=ADMIN_ADD_FORECAST_CALLBACK)
    return builder.as_markup()


def build_admin_months_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for month, name in MONTH_NAMES_RU.items():
        builder.button(text=name, callback_data=f"admin-month:{month:02d}")
    builder.adjust(3)
    return builder.as_markup()


def build_admin_signs_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sign, name in SIGNS_RU.items():
        builder.button(text=name, callback_data=f"admin-sign:{sign}")
    builder.adjust(3)
    return builder.as_markup()

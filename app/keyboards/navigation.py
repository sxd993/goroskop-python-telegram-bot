from pathlib import Path

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import SIGNS_RU
from app.services import media


def build_years_keyboard(years):
    builder = InlineKeyboardBuilder()
    for year in years:
        builder.button(text=year, callback_data=f"year:{year}")
    builder.adjust(3)
    return builder.as_markup()


def build_months_keyboard(media_dir: Path, year: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ym in media.months_for_year(media_dir, year):
        name = media.month_name_from_ym(ym)
        if name:
            builder.button(text=name, callback_data=f"month:{ym}")
    builder.adjust(3)
    return builder.as_markup()


def build_signs_keyboard(media_dir: Path, ym: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sign in media.available_signs(media_dir, ym):
        name = SIGNS_RU[sign]
        builder.button(text=name, callback_data=f"sign:{ym}:{sign}")
    builder.adjust(3)
    return builder.as_markup()


def build_pay_keyboard(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Оплатить", callback_data=f"pay:{order_id}")]]
    )

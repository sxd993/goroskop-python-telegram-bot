from pathlib import Path

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import SIGNS_RU
from app.services import media


def build_layout_keyboard(*, has_year: bool, has_month: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_year:
        builder.button(text="Годовой гороскоп", callback_data="mode:year")
    if has_month:
        builder.button(text="Месячный гороскоп", callback_data="mode:month")
    builder.adjust(1)
    return builder.as_markup()


def build_years_keyboard(years, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for year in years:
        builder.button(text=year, callback_data=f"{prefix}:{year}")
    builder.adjust(3)
    return builder.as_markup()


def build_months_keyboard(media_dir: Path, year: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ym in media.months_for_year(media_dir, year):
        name = media.month_name_from_ym(ym)
        if name:
            builder.button(text=name, callback_data=f"m-month:{ym}")
    builder.adjust(3)
    return builder.as_markup()


def build_month_signs_keyboard(media_dir: Path, ym: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sign in media.available_month_signs(media_dir, ym):
        name = SIGNS_RU[sign]
        builder.button(text=name, callback_data=f"m-sign:{ym}:{sign}")
    builder.adjust(3)
    return builder.as_markup()


def build_year_signs_keyboard(media_dir: Path, year: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sign in media.available_year_signs(media_dir, year):
        name = SIGNS_RU[sign]
        builder.button(text=name, callback_data=f"y-sign:{year}:{sign}")
    builder.adjust(3)
    return builder.as_markup()


def build_pay_keyboard(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Оплатить", callback_data=f"pay:{order_id}")]]
    )

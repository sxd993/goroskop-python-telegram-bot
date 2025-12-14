import logging
from pathlib import Path
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import catalog
from const import SIGNS_RU

logger = logging.getLogger(__name__)


def build_years_keyboard(years):
    builder = InlineKeyboardBuilder()
    for year in years:
        builder.button(text=year, callback_data=f"year:{year}")
    builder.adjust(3)
    return builder.as_markup()


def build_months_keyboard(media_dir: Path, year: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ym in catalog.months_for_year(media_dir, year):
        name = catalog.month_name_from_ym(ym)
        if name:
            builder.button(text=name, callback_data=f"month:{ym}")
    builder.adjust(3)
    return builder.as_markup()


def build_signs_keyboard(media_dir: Path, ym: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sign in catalog.available_signs(media_dir, ym):
        name = SIGNS_RU[sign]
        builder.button(text=name, callback_data=f"sign:{ym}:{sign}")
    builder.adjust(3)
    return builder.as_markup()


def build_pay_keyboard(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Оплатить", callback_data=f"pay:{order_id}")]]
    )


def parse_month_data(data: str) -> Optional[str]:
    if not data.startswith("month:"):
        return None
    ym = data.split(":", maxsplit=1)[1]
    return ym if catalog.parse_year_month(ym) else None


def parse_year_data(data: str) -> Optional[str]:
    if not data.startswith("year:"):
        return None
    year = data.split(":", maxsplit=1)[1]
    return year if catalog.is_valid_year(year) else None


def parse_sign_data(data: str) -> Optional[Tuple[str, str]]:
    if not data.startswith("sign:"):
        return None
    parts = data.split(":")
    if len(parts) != 3:
        return None
    _, ym, sign = parts
    if not catalog.parse_year_month(ym) or sign not in SIGNS_RU:
        return None
    return ym, sign


def parse_pay_data(data: str) -> Optional[str]:
    if not data.startswith("pay:"):
        return None
    return data.split(":", maxsplit=1)[1]


def parse_product(product_id: str) -> Optional[Tuple[str, str]]:
    parts = product_id.split(":")
    if len(parts) != 2:
        return None
    ym, sign = parts
    if not catalog.parse_year_month(ym) or sign not in SIGNS_RU:
        return None
    return ym, sign


async def send_content(bot: Bot, chat_id: int, path: Path, caption: str) -> bool:
    try:
        await bot.send_document(chat_id, FSInputFile(path), caption=caption)
        return True
    except Exception:
        logger.exception("Failed to send content %s", path)
        return False

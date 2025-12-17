import datetime as dt
import logging
from pathlib import Path
from typing import Optional

from aiogram.types import CallbackQuery, Message

from app.features import texts
from app.config import SIGNS_RU
from app.services import media
from app.services.parsing import parse_product

logger = logging.getLogger(__name__)

REVIEWS_PAGE_SIZE = 5


def product_label(product_id: str) -> str:
    parsed = parse_product(product_id)
    if not parsed:
        return product_id
    sign_name = SIGNS_RU.get(parsed["sign"], parsed["sign"])
    if parsed["kind"] == "month" and parsed["month"]:
        ym = f"{parsed['year']}-{parsed['month']}"
        month_name = media.month_name_from_ym(ym) or ym
        return f"{month_name} {parsed['year']}, {sign_name}"
    return f"{parsed['year']} год, {sign_name}"


def format_dt(value: str) -> str:
    try:
        return dt.datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return value


async def edit_or_send(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    try:
        if callback.message:
            await callback.message.edit_text(text, reply_markup=reply_markup)
            return
    except Exception:
        logger.exception("Failed to edit message for callback")
    if callback.message:
        await callback.message.answer(text, reply_markup=reply_markup)


def review_destination_path(media_dir: Path, sign: str, extension: str) -> Path:
    target_dir = media_dir / "reviews" / sign
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{sign}.{extension}"


def detect_extension(message: Message) -> Optional[str]:
    if message.document and message.document.file_name:
        parts = message.document.file_name.rsplit(".", maxsplit=1)
        if len(parts) == 2:
            return parts[-1].lower()
    if message.photo:
        return "jpg"
    return None


def destination_path(kind: str, media_dir: Path, year: str, sign: str, extension: str, month: str | None) -> Path:
    if kind == "year":
        target_dir = media_dir / "year" / year
    else:
        target_dir = media_dir / "month" / year / (month or "01")
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{sign}.{extension}"


async def save_media(message: Message, destination: Path) -> bool:
    if not message.document and not message.photo:
        return False
    file_to_download = message.document or message.photo[-1]
    try:
        await message.bot.download(file_to_download, destination=destination)
        return True
    except Exception:
        logger.exception("Failed to download media to %s", destination)
        return False

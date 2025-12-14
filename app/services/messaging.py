import logging
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)


async def send_content(bot: Bot, chat_id: int, path: Path, caption: str) -> bool:
    try:
        await bot.send_document(chat_id, FSInputFile(path), caption=caption)
        return True
    except Exception:
        logger.exception("Failed to send content %s", path)
        return False

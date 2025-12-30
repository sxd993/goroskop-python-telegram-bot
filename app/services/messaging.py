import asyncio
import logging
from pathlib import Path
from typing import Awaitable, Callable, Optional

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import FSInputFile, InputMediaPhoto

logger = logging.getLogger(__name__)

TelegramCall = Callable[[], Awaitable[object]]


async def send_with_retry(call: TelegramCall, *, attempts: int = 3, base_delay: float = 1.0) -> None:
    last_exc: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            await call()
            return
        except TelegramRetryAfter as exc:
            delay = max(base_delay * attempt, exc.retry_after)
            logger.warning("Telegram rate limit (429). retry_in=%s", delay)
            last_exc = exc
            await asyncio.sleep(delay)
        except TelegramServerError as exc:
            delay = base_delay * attempt
            logger.warning("Telegram server error status=%s retry_in=%s", exc.status_code, delay)
            last_exc = exc
            await asyncio.sleep(delay)
        except TelegramNetworkError as exc:
            delay = base_delay * attempt
            logger.warning("Telegram network error retry_in=%s", delay)
            last_exc = exc
            await asyncio.sleep(delay)
        except TelegramAPIError as exc:
            status_code = getattr(exc, "status_code", None)
            description = getattr(exc, "message", str(exc))
            logger.error("Telegram API error status=%s description=%s", status_code, description)
            last_exc = exc
            break
        except Exception as exc:  # pragma: no cover - fallback
            last_exc = exc
            logger.exception("Unexpected Telegram error: %s", exc)
            break
    if last_exc:
        raise last_exc


async def send_content(bot: Bot, chat_id: int, path: Path, caption: Optional[str] = None) -> bool:
    try:
        mtime_tag = int(path.stat().st_mtime)
        filename = f"{path.stem}-{mtime_tag}{path.suffix}"
        await send_with_retry(
            lambda: bot.send_document(chat_id, FSInputFile(path, filename=filename), caption=caption)
        )
        return True
    except Exception:
        logger.exception("Failed to send content %s", path)
        return False


async def send_contents(bot: Bot, chat_id: int, paths: list[Path], caption: str) -> bool:
    if not paths:
        return False
    if len(paths) == 1:
        return await send_content(bot, chat_id, paths[0], caption=caption)
    chunk_size = 10
    for start in range(0, len(paths), chunk_size):
        chunk = paths[start:start + chunk_size]
        media: list[InputMediaPhoto] = []
        for index, path in enumerate(chunk):
            mtime_tag = int(path.stat().st_mtime)
            filename = f"{path.stem}-{mtime_tag}{path.suffix}"
            item_caption = caption if start == 0 and index == 0 else None
            media.append(InputMediaPhoto(media=FSInputFile(path, filename=filename), caption=item_caption))
        try:
            await send_with_retry(lambda: bot.send_media_group(chat_id, media=media))
        except Exception:
            logger.exception("Failed to send media group chunk starting at %s", start)
            return False
    return True


async def send_message_safe(bot: Bot, chat_id: int, text: str, **kwargs) -> bool:
    try:
        await send_with_retry(lambda: bot.send_message(chat_id, text, **kwargs))
        return True
    except Exception:
        logger.exception("Failed to send message to chat=%s", chat_id)
        return False

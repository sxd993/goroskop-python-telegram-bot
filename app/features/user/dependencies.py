from pathlib import Path

from aiogram import Bot

from app.config import Settings
from app.services import state_machine

_settings: Settings | None = None


def setup_user_settings(settings: Settings) -> None:
    global _settings
    _settings = settings


def get_settings(bot: Bot) -> Settings:
    if _settings is None:
        raise RuntimeError("Handlers are not configured with settings")
    return _settings


def get_db_path(bot: Bot) -> Path:
    return get_settings(bot).db_path


async def ensure_user(bot: Bot, user_id: int) -> None:
    await state_machine.get_user_state(get_db_path(bot), user_id)

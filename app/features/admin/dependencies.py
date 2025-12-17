from typing import Optional

from aiogram import Bot

from app.config import Settings

_settings: Settings | None = None


def setup_admin_settings(settings: Settings) -> None:
    global _settings
    _settings = settings


def get_settings(bot: Bot) -> Settings:
    if _settings is None:
        raise RuntimeError("Handlers are not configured with settings")
    return _settings


def is_admin(bot: Bot, user_id: Optional[int]) -> bool:
    settings = get_settings(bot)
    return bool(user_id and user_id in settings.admin_ids)

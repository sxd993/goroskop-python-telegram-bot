from pathlib import Path
from typing import Dict

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# === Константы и словари ===
YEAR_MONTH_PATTERN = r"^(?P<year>\d{4})-(?P<month>\d{2})$"
ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png", "webp")

MONTH_NAMES_RU = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}

SIGNS_RU: Dict[str, str] = {
    "aries": "Овен",
    "taurus": "Телец",
    "gemini": "Близнецы",
    "cancer": "Рак",
    "leo": "Лев",
    "virgo": "Дева",
    "libra": "Весы",
    "scorpio": "Скорпион",
    "sagittarius": "Стрелец",
    "capricorn": "Козерог",
    "aquarius": "Водолей",
    "pisces": "Рыбы",
}


class Settings(BaseSettings):
    bot_token: str = Field(..., alias="BOT_TOKEN")
    provider_token: str = Field(..., alias="PROVIDER_TOKEN")
    price_kopeks: int = Field(39000, alias="PRICE_KOPEKS")
    currency: str = Field("RUB", alias="CURRENCY")
    media_dir: Path = Field(Path("media"), alias="MEDIA_DIR")
    db_path: Path = Field(Path("data/bot.sqlite3"), alias="DB_PATH")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=True)


def load_settings() -> Settings:
    settings = Settings()
    settings.media_dir = settings.media_dir.expanduser().resolve()
    settings.db_path = settings.db_path.expanduser().resolve()
    return settings

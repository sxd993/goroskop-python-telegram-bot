import os
from pathlib import Path
from typing import Dict, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource, EnvSettingsSource

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

PRICE_KOPEKS_BY_KIND: Dict[str, int] = {
    "month": 39000,
    "year": 99000,
}


class Settings(BaseSettings):
    bot_token: str = Field(..., alias="BOT_TOKEN")
    provider_token: str = Field(..., alias="PROVIDER_TOKEN")
    currency: str = Field("RUB", alias="CURRENCY")
    media_dir: Path = Field(Path("media"), alias="MEDIA_DIR")
    db_path: Path = Field(Path("data/bot.sqlite3"), alias="DB_PATH")
    pricing_path: Path = Field(Path("data/pricing.json"), alias="PRICING_PATH")
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=True,
    )

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value):  # type: ignore[no-untyped-def]
        if value is None:
            return []
        if isinstance(value, str):
            items = [
                part.strip()
                for part in value.replace(";", ",").split(",")
                if part.strip()
            ]
            return [int(item) for item in items]
        if isinstance(value, int):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return [int(item) for item in value]
        raise TypeError("ADMIN_IDS must be a comma-separated list or array of integers")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,  # type: ignore[override]
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """
        Keep raw env strings for complex fields (e.g., ADMIN_IDS="1,2,3") by bypassing JSON parsing.
        """

        class _NoJsonEnvSource(EnvSettingsSource):
            def decode_complex_value(self, field_name, field, value):
                return value

        class _NoJsonDotEnvSource(DotEnvSettingsSource):
            def decode_complex_value(self, field_name, field, value):
                return value

        return (
            init_settings,
            _NoJsonEnvSource(
                settings_cls,
                case_sensitive=env_settings.case_sensitive,
                env_prefix=env_settings.env_prefix,
                env_nested_delimiter=env_settings.env_nested_delimiter,
                env_ignore_empty=env_settings.env_ignore_empty,
                env_parse_none_str=env_settings.env_parse_none_str,
            ),
            _NoJsonDotEnvSource(
                settings_cls,
                env_file=dotenv_settings.env_file,
                env_file_encoding=dotenv_settings.env_file_encoding,
                case_sensitive=dotenv_settings.case_sensitive,
                env_prefix=dotenv_settings.env_prefix,
                env_nested_delimiter=dotenv_settings.env_nested_delimiter,
                env_ignore_empty=dotenv_settings.env_ignore_empty,
                env_parse_none_str=dotenv_settings.env_parse_none_str,
            ),
            file_secret_settings,
        )


def load_settings() -> Settings:
    env_file = _resolve_env_file()
    settings = Settings(_env_file=str(env_file)) if env_file is not None else Settings()
    settings.media_dir = settings.media_dir.expanduser().resolve()
    settings.db_path = settings.db_path.expanduser().resolve()
    settings.pricing_path = settings.pricing_path.expanduser().resolve()
    return settings


def _resolve_env_file(explicit: str | Path | None = None) -> Path | None:
    """
    Allow switching env files without renaming:
    - explicit argument (internal API)
    - ENV_FILE=/path/to/.env.something
    - APP_ENV=test -> .env.test

    If nothing is set, fall back to SettingsConfigDict(env_file=".env").
    """

    candidate: str | Path | None = explicit
    if candidate is None:
        candidate = os.getenv("ENV_FILE") or None
    if candidate is None:
        app_env = os.getenv("APP_ENV") or None
        if app_env:
            candidate = f".env.{app_env}"

    if candidate is None:
        return None

    path = Path(candidate).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()

    if not path.exists():
        raise FileNotFoundError(
            f"Env file not found: {path}. "
            "Set ENV_FILE to an existing path or APP_ENV to match an existing .env.<name>."
        )

    return path

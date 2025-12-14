from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

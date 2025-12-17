import sys
from pathlib import Path

import asyncio

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def settings(tmp_path: Path):
    from app.config import Settings
    from app.features.user.handlers import setup_handlers

    db_path = tmp_path / "db.sqlite3"
    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    cfg = Settings(
        BOT_TOKEN="TEST",
        PROVIDER_TOKEN="TEST_PROVIDER",
        MEDIA_DIR=media_dir,
        DB_PATH=db_path,
        CURRENCY="RUB",
        ADMIN_IDS=[],
    )
    cfg.media_dir = media_dir
    cfg.db_path = db_path
    setup_handlers(cfg)
    return cfg


@pytest.fixture
def initialized_db(settings):
    from app.services import db

    asyncio.run(db.init_db(settings.db_path))
    return settings.db_path

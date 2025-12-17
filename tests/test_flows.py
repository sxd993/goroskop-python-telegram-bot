import asyncio
from pathlib import Path

import pytest

from app.config import Settings
from app.features.user.handlers import handle_review_text, setup_handlers
from app.services import db, payments, state_machine
from app.services.payments import PaymentStatus
from app.services.state_machine import UserState


class DummyBot:
    def __init__(self):
        self.sent_messages: list[str] = []

    async def send_message(self, chat_id: int, text: str, **kwargs):  # pragma: no cover - compatibility
        self.sent_messages.append(text)


class DummyMessage:
    def __init__(self, text: str, user_id: int, chat_id: int, bot):
        self.text = text
        self.from_user = type("obj", (), {"id": user_id})()
        self.chat = type("obj", (), {"id": chat_id})()
        self.bot = bot
        self.answers: list[str] = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    db_path = tmp_path / "db.sqlite3"
    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    cfg = Settings(
        BOT_TOKEN="TEST",
        PROVIDER_TOKEN="TEST_PROVIDER",
        MEDIA_DIR=media_dir,
        DB_PATH=db_path,
        PRICE_KOPEKS=1000,
        CURRENCY="RUB",
        ADMIN_IDS=[],
    )
    cfg.media_dir = media_dir
    cfg.db_path = db_path
    setup_handlers(cfg)
    return cfg


@pytest.fixture
def initialized_db(settings: Settings) -> Path:
    asyncio.run(db.init_db(settings.db_path))
    return settings.db_path


def test_success_payment_flow_sets_review_pending(initialized_db: Path):
    async def scenario():
        user_id = 10
        order = await db.create_order(initialized_db, user_id, "year:2024:aries", 1000, "RUB")
        await state_machine.set_order_initiated(initialized_db, user_id, order["id"])
        await db.mark_invoice_sent(initialized_db, order["id"])
        await state_machine.set_payment_pending(initialized_db, user_id, order["id"])

        result = await payments.handle_webhook(
            initialized_db,
            order_id=order["id"],
            provider_tx_id="tx-1",
            status=PaymentStatus.SUCCESS,
            amount_kopeks=1000,
            currency="RUB",
            payload="payload",
        )
        assert result["applied"] is True
        await state_machine.set_paid(initialized_db, user_id, order["id"])

        refreshed = await db.get_order(initialized_db, order["id"])
        assert refreshed is not None
        assert refreshed["status"] == "paid"

        await db.mark_delivered(initialized_db, order["id"])
        await state_machine.set_delivered(initialized_db, user_id, order["id"])
        await state_machine.set_review_pending(initialized_db, user_id, order["id"])

        user = await db.get_user(initialized_db, user_id)
        assert user is not None
        assert user["state"] == UserState.REVIEW_PENDING.value

    asyncio.run(scenario())


def test_duplicate_webhook_does_not_reapply(initialized_db: Path):
    async def scenario():
        user_id = 20
        order = await db.create_order(initialized_db, user_id, "year:2025:aries", 1000, "RUB")
        await state_machine.set_order_initiated(initialized_db, user_id, order["id"])
        await state_machine.set_payment_pending(initialized_db, user_id, order["id"])

        first = await payments.handle_webhook(
            initialized_db,
            order_id=order["id"],
            provider_tx_id="tx-dup",
            status=PaymentStatus.SUCCESS,
            amount_kopeks=1000,
            currency="RUB",
            payload="payload",
        )
        second = await payments.handle_webhook(
            initialized_db,
            order_id=order["id"],
            provider_tx_id="tx-dup",
            status=PaymentStatus.SUCCESS,
            amount_kopeks=1000,
            currency="RUB",
            payload="payload",
        )

        assert first["applied"] is True
        assert second["applied"] is False
        assert second["reason"].startswith("duplicate")
        refreshed = await db.get_order(initialized_db, order["id"])
        assert refreshed is not None
        assert refreshed["status"] == "paid"

    asyncio.run(scenario())


def test_message_ignored_when_not_review_pending(settings: Settings, initialized_db: Path):
    async def scenario():
        user_id = 30
        await state_machine.set_order_initiated(initialized_db, user_id, "order-x")
        await state_machine.set_payment_pending(initialized_db, user_id, "order-x")
        await state_machine.set_paid(initialized_db, user_id, "order-x")
        dummy_bot = DummyBot()
        message = DummyMessage("Спасибо!", user_id, user_id, dummy_bot)

        await handle_review_text(message)

        pending = await db.get_pending_review_for_user(initialized_db, user_id)
        assert pending is None
        assert not message.answers

    asyncio.run(scenario())


def test_failed_payment_keeps_unpaid_state(initialized_db: Path):
    async def scenario():
        user_id = 40
        order = await db.create_order(initialized_db, user_id, "year:2026:aries", 1000, "RUB")
        await state_machine.set_order_initiated(initialized_db, user_id, order["id"])
        await state_machine.set_payment_pending(initialized_db, user_id, order["id"])

        result = await payments.handle_webhook(
            initialized_db,
            order_id=order["id"],
            provider_tx_id="tx-failed",
            status=PaymentStatus.FAILED,
            amount_kopeks=1000,
            currency="RUB",
            payload="payload",
        )

        assert result["applied"] is True
        refreshed = await db.get_order(initialized_db, order["id"])
        assert refreshed is not None
        assert refreshed["status"] == "failed"
        user = await db.get_user(initialized_db, user_id)
        assert user is not None
        assert user["state"] != UserState.PAID.value

    asyncio.run(scenario())

import asyncio

import pytest

from app.features.user.handlers import handle_start
from app.services import db
from app.services.state_machine import UserState


class DummyMessage:
    def __init__(self, bot, user_id: int):
        self.bot = bot
        self.from_user = type("obj", (), {"id": user_id})()
        self.answers: list[str] = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)


@pytest.mark.usefixtures("initialized_db")
def test_start_resets_review_pending_state(settings, initialized_db):
    async def scenario():
        user_id = 123
        await db.ensure_user(initialized_db, user_id, UserState.REVIEW_PENDING.value, last_order_id="order-1")

        message = DummyMessage(bot=object(), user_id=user_id)
        await handle_start(message)

        user = await db.get_user(initialized_db, user_id)
        assert user is not None
        assert user["state"] == UserState.IDLE.value

    asyncio.run(scenario())


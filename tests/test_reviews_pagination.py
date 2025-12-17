import asyncio
import datetime as dt
import uuid

import aiosqlite
import pytest

from app.services import db


@pytest.mark.usefixtures("initialized_db")
def test_fetch_reviews_page_and_get_review(initialized_db):
    async def scenario():
        async with aiosqlite.connect(initialized_db) as conn:
            await conn.execute("PRAGMA foreign_keys = ON")

            base = dt.datetime(2025, 1, 1, 12, 0, 0)
            inserted_ids: list[str] = []

            for i in range(12):
                order_id = str(uuid.uuid4())
                review_id = str(uuid.uuid4())
                created_at = (base + dt.timedelta(days=i)).isoformat()
                product_id = f"year:202{i % 10}:aries"

                await conn.execute(
                    """
                    INSERT INTO orders (id, user_id, product_id, amount_kopeks, currency, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (order_id, 100 + i, product_id, 1000, "RUB", "paid", created_at),
                )
                await conn.execute(
                    """
                    INSERT INTO reviews (id, order_id, user_id, product_id, status, text, created_at, answered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (review_id, order_id, 100 + i, product_id, "submitted", f"text {i}", created_at, created_at),
                )
                inserted_ids.append(review_id)

            await conn.commit()

        page1 = await db.fetch_reviews_page(initialized_db, limit=5, offset=0)
        assert len(page1) == 5
        assert page1[0]["created_at"] > page1[-1]["created_at"]

        page2 = await db.fetch_reviews_page(initialized_db, limit=5, offset=5)
        assert len(page2) == 5
        assert page1[-1]["created_at"] > page2[0]["created_at"]

        target_id = inserted_ids[3]
        got = await db.get_review(initialized_db, target_id)
        assert got is not None
        assert got["id"] == target_id

    asyncio.run(scenario())


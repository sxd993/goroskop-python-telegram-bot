import asyncio

from app.services import db


def test_fetch_paid_months_page_and_breakdown(initialized_db):
    async def scenario():
        user_id = 1
        currency = "RUB"

        await db.create_paid_order(
            initialized_db,
            user_id=user_id,
            product_id="month:2025-12:aries",
            amount_kopeks=1000,
            currency=currency,
            telegram_charge_id="ch-1",
        )
        await db.create_paid_order(
            initialized_db,
            user_id=user_id,
            product_id="month:2025-12:aries",
            amount_kopeks=2000,
            currency=currency,
            telegram_charge_id="ch-2",
        )
        await db.create_paid_order(
            initialized_db,
            user_id=user_id,
            product_id="month:2025-12:taurus",
            amount_kopeks=500,
            currency=currency,
            telegram_charge_id="ch-3",
        )
        await db.create_paid_order(
            initialized_db,
            user_id=user_id,
            product_id="month:2025-11:aries",
            amount_kopeks=700,
            currency=currency,
            telegram_charge_id="ch-4",
        )
        await db.create_paid_order(
            initialized_db,
            user_id=user_id,
            product_id="year:2025:aries",
            amount_kopeks=9000,
            currency=currency,
            telegram_charge_id="ch-5",
        )

        months = await db.fetch_paid_months_page(initialized_db, limit=10, offset=0)
        assert months == ["2025-12", "2025-11"]

        breakdown = await db.fetch_month_sales_breakdown(initialized_db, ym="2025-12")
        assert breakdown == [
            ("aries", 2, 3000),
            ("taurus", 1, 500),
        ]

    asyncio.run(scenario())


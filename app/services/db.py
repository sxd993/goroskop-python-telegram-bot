import datetime as dt
import uuid
from pathlib import Path
from typing import Optional

import aiosqlite

from app.models import Order


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    product_id TEXT NOT NULL,
    amount_kopeks INTEGER NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL,
    telegram_charge_id TEXT UNIQUE,
    created_at TEXT NOT NULL,
    paid_at TEXT,
    delivered_at TEXT
);
"""


def _now_iso() -> str:
    return dt.datetime.utcnow().isoformat()


async def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()


async def create_order(
    db_path: Path,
    user_id: int,
    product_id: str,
    amount_kopeks: int,
    currency: str,
) -> Order:
    order_id = str(uuid.uuid4())
    created_at = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO orders (id, user_id, product_id, amount_kopeks, currency, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (order_id, user_id, product_id, amount_kopeks, currency, "created", created_at),
        )
        await db.commit()
    return {
        "id": order_id,
        "user_id": user_id,
        "product_id": product_id,
        "amount_kopeks": amount_kopeks,
        "currency": currency,
        "status": "created",
        "created_at": created_at,
        "paid_at": None,
        "delivered_at": None,
        "telegram_charge_id": None,
    }


async def get_order(db_path: Path, order_id: str) -> Optional[Order]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
            row = await cursor.fetchone()
            return Order(dict(row)) if row else None


async def update_status(db_path: Path, order_id: str, status: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        await db.commit()


async def mark_invoice_sent(db_path: Path, order_id: str) -> None:
    await update_status(db_path, order_id, "invoice_sent")


async def mark_paid(
    db_path: Path,
    order_id: str,
    telegram_charge_id: str,
) -> None:
    paid_at = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE orders
            SET status = 'paid',
                paid_at = COALESCE(paid_at, ?),
                telegram_charge_id = COALESCE(telegram_charge_id, ?)
            WHERE id = ?
            """,
            (paid_at, telegram_charge_id, order_id),
        )
        await db.commit()


async def mark_delivered(db_path: Path, order_id: str) -> None:
    delivered_at = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE orders
            SET delivered_at = COALESCE(delivered_at, ?)
            WHERE id = ?
            """,
            (delivered_at, order_id),
        )
        await db.commit()

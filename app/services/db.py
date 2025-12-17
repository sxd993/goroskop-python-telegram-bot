import datetime as dt
import uuid
from pathlib import Path
from typing import Optional

import aiosqlite

from app.models import Order, Payment, Review, User


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

CREATE_USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL,
    last_order_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(last_order_id) REFERENCES orders(id)
);
"""

CREATE_PAYMENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    provider_tx_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    amount_kopeks INTEGER NOT NULL,
    currency TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id)
);
"""

CREATE_REVIEWS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    product_id TEXT NOT NULL,
    status TEXT NOT NULL,
    text TEXT,
    created_at TEXT NOT NULL,
    answered_at TEXT,
    FOREIGN KEY(order_id) REFERENCES orders(id)
);
"""


def _now_iso() -> str:
    return dt.datetime.utcnow().isoformat()


async def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.execute(CREATE_USERS_TABLE_SQL)
        await db.execute(CREATE_PAYMENTS_TABLE_SQL)
        await db.execute(CREATE_REVIEWS_TABLE_SQL)
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


async def create_paid_order(
    db_path: Path,
    user_id: int,
    product_id: str,
    amount_kopeks: int,
    currency: str,
    telegram_charge_id: str,
) -> Order:
    order_id = str(uuid.uuid4())
    now = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO orders (id, user_id, product_id, amount_kopeks, currency, status, created_at, paid_at, telegram_charge_id)
            VALUES (?, ?, ?, ?, ?, 'paid', ?, ?, ?)
            """,
            (order_id, user_id, product_id, amount_kopeks, currency, now, now, telegram_charge_id),
        )
        await db.commit()
    return {
        "id": order_id,
        "user_id": user_id,
        "product_id": product_id,
        "amount_kopeks": amount_kopeks,
        "currency": currency,
        "status": "paid",
        "created_at": now,
        "paid_at": now,
        "delivered_at": None,
        "telegram_charge_id": telegram_charge_id,
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


async def mark_payment_failed(db_path: Path, order_id: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE orders
            SET status = 'failed'
            WHERE id = ? AND status != 'paid'
            """,
            (order_id,),
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


async def fetch_sales_stats(db_path: Path) -> list[tuple[str, int, int]]:
    """
    Returns list of tuples: (product_id, paid_count, total_amount_kopeks)
    """
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT product_id, COUNT(*) AS paid_count, SUM(amount_kopeks) AS total_amount
            FROM orders
            WHERE status = 'paid'
            GROUP BY product_id
            ORDER BY paid_count DESC, product_id ASC
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [(row[0], row[1], row[2]) for row in rows]


async def create_review_request(
    db_path: Path,
    order_id: str,
    user_id: int,
    product_id: str,
) -> Review:
    review_id = str(uuid.uuid4())
    now = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO reviews (id, order_id, user_id, product_id, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (review_id, order_id, user_id, product_id, now),
        )
        await db.execute(
            """
            UPDATE reviews
            SET status = 'pending',
                text = NULL,
                answered_at = NULL
            WHERE order_id = ? AND status != 'submitted'
            """,
            (order_id,),
        )
        await db.commit()
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reviews WHERE order_id = ?", (order_id,)) as cursor:
            row = await cursor.fetchone()
            return Review(dict(row)) if row else {
                "id": review_id,
                "order_id": order_id,
                "user_id": user_id,
                "product_id": product_id,
                "status": "pending",
                "text": None,
                "created_at": now,
                "answered_at": None,
            }


async def mark_review_submitted(db_path: Path, order_id: str, text: str) -> None:
    answered_at = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE reviews
            SET status = 'submitted',
                text = ?,
                answered_at = COALESCE(answered_at, ?)
            WHERE order_id = ?
            """,
            (text, answered_at, order_id),
        )
        await db.commit()


async def mark_review_declined(db_path: Path, order_id: str, user_id: int, product_id: str) -> None:
    await create_review_request(db_path, order_id, user_id, product_id)
    answered_at = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE reviews
            SET status = 'declined',
                answered_at = COALESCE(answered_at, ?)
            WHERE order_id = ? AND status != 'submitted'
            """,
            (answered_at, order_id),
        )
        await db.commit()


async def get_pending_review_for_user(db_path: Path, user_id: int) -> Optional[Review]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT *
            FROM reviews
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return Review(dict(row)) if row else None


async def fetch_recent_reviews(db_path: Path, limit: int = 30) -> list[Review]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT *
            FROM reviews
            WHERE status IN ('submitted', 'declined')
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [Review(dict(row)) for row in rows]


async def get_user(db_path: Path, user_id: int) -> Optional[User]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return User(dict(row)) if row else None


async def ensure_user(db_path: Path, user_id: int, state: str, last_order_id: Optional[str]) -> User:
    now = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, state, last_order_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id, state, last_order_id, now, now),
        )
        await db.commit()
    user = await get_user(db_path, user_id)
    if user:
        return user
    return {
        "user_id": user_id,
        "state": state,
        "last_order_id": last_order_id,
        "created_at": now,
        "updated_at": now,
    }


async def update_user_state(db_path: Path, user_id: int, state: str, last_order_id: Optional[str]) -> User:
    now = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE users
            SET state = ?,
                last_order_id = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (state, last_order_id, now, user_id),
        )
        await db.commit()
    user = await get_user(db_path, user_id)
    if not user:
        return {
            "user_id": user_id,
            "state": state,
            "last_order_id": last_order_id,
            "created_at": now,
            "updated_at": now,
        }
    return user


async def create_payment(
    db_path: Path,
    order_id: str,
    provider_tx_id: str,
    status: str,
    amount_kopeks: int,
    currency: str,
    payload: str,
) -> Payment:
    now = _now_iso()
    payment_id = str(uuid.uuid4())
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO payments (id, order_id, provider_tx_id, status, amount_kopeks, currency, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (payment_id, order_id, provider_tx_id, status, amount_kopeks, currency, payload, now, now),
        )
        await db.commit()
    return {
        "id": payment_id,
        "order_id": order_id,
        "provider_tx_id": provider_tx_id,
        "status": status,
        "amount_kopeks": amount_kopeks,
        "currency": currency,
        "payload": payload,
        "created_at": now,
        "updated_at": now,
    }


async def get_payment_by_provider_id(db_path: Path, provider_tx_id: str) -> Optional[Payment]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE provider_tx_id = ?",
            (provider_tx_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return Payment(dict(row)) if row else None


async def update_payment_status(db_path: Path, provider_tx_id: str, status: str) -> None:
    now = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE payments
            SET status = ?,
                updated_at = ?
            WHERE provider_tx_id = ?
            """,
            (status, now, provider_tx_id),
        )
        await db.commit()

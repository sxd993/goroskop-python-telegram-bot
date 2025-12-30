import datetime as dt
import uuid
from pathlib import Path
from typing import Optional

import aiosqlite

from app.models import Campaign, CampaignAudience, CampaignResponse, Order, Payment, Review, User


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
    contact_phone TEXT,
    contact_username TEXT,
    created_at TEXT NOT NULL,
    answered_at TEXT,
    FOREIGN KEY(order_id) REFERENCES orders(id)
);
"""

CREATE_CAMPAIGNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    price_kopeks INTEGER NOT NULL,
    interest_redirect TEXT NOT NULL
);
"""

CREATE_CAMPAIGN_AUDIENCE_SQL = """
CREATE TABLE IF NOT EXISTS campaign_audience (
    campaign_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    message_id INTEGER,
    error TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (campaign_id, user_id),
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
"""

CREATE_CAMPAIGN_RESPONSES_SQL = """
CREATE TABLE IF NOT EXISTS campaign_responses (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    full_name TEXT,
    birthdate TEXT,
    phone TEXT,
    raw_text TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);
"""


def _now_iso() -> str:
    return dt.datetime.utcnow().isoformat()


async def _ensure_campaigns_table(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("PRAGMA table_info(campaigns)")
    rows = await cursor.fetchall()
    columns = [row[1] for row in rows]
    expected = {"id", "title", "body", "price_kopeks", "interest_redirect"}
    if not columns:
        await db.execute(CREATE_CAMPAIGNS_TABLE_SQL)
        return
    if set(columns) == expected:
        return

    legacy_name = f"campaigns_legacy_{int(dt.datetime.utcnow().timestamp())}"
    await db.execute(f"ALTER TABLE campaigns RENAME TO {legacy_name}")
    await db.execute(CREATE_CAMPAIGNS_TABLE_SQL)
    await db.execute(
        f"""
        INSERT INTO campaigns (id, title, body, price_kopeks, interest_redirect)
        SELECT id, title, body, price_kopeks, '' FROM {legacy_name}
        """
    )
    await db.execute(f"DROP TABLE {legacy_name}")
    await db.commit()


async def _ensure_reviews_table(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("PRAGMA table_info(reviews)")
    rows = await cursor.fetchall()
    if not rows:
        await db.execute(CREATE_REVIEWS_TABLE_SQL)
        return
    columns = {row[1] for row in rows}
    if "contact_phone" not in columns:
        await db.execute("ALTER TABLE reviews ADD COLUMN contact_phone TEXT")
    if "contact_username" not in columns:
        await db.execute("ALTER TABLE reviews ADD COLUMN contact_username TEXT")
    await db.commit()


async def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.execute(CREATE_USERS_TABLE_SQL)
        await db.execute(CREATE_PAYMENTS_TABLE_SQL)
        await _ensure_reviews_table(db)
        await _ensure_campaigns_table(db)
        await db.execute(CREATE_CAMPAIGN_AUDIENCE_SQL)
        await db.execute(CREATE_CAMPAIGN_RESPONSES_SQL)
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


async def fetch_paid_months_page(db_path: Path, *, limit: int, offset: int) -> list[str]:
    """
    Returns distinct YYYY-MM values for paid monthly products, ordered by newest first.
    """
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT DISTINCT substr(product_id, 7, 7) AS ym
            FROM orders
            WHERE status = 'paid' AND product_id LIKE 'month:%'
            ORDER BY ym DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def fetch_month_sales_breakdown(db_path: Path, *, ym: str) -> list[tuple[str, int, int]]:
    """
    Returns list of tuples: (sign, paid_count, total_amount_kopeks) for a given YYYY-MM month product.
    """
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT
                substr(product_id, length('month:' || ? || ':') + 1) AS sign,
                COUNT(*) AS paid_count,
                SUM(amount_kopeks) AS total_amount
            FROM orders
            WHERE status = 'paid' AND product_id LIKE ('month:' || ? || ':%')
            GROUP BY sign
            ORDER BY paid_count DESC, sign ASC
            """,
            (ym, ym),
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
                "contact_phone": None,
                "contact_username": None,
                "created_at": now,
                "answered_at": None,
            }


async def update_review_contact(
    db_path: Path,
    order_id: str,
    user_id: int,
    *,
    phone: Optional[str] = None,
    username: Optional[str] = None,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE reviews
            SET contact_phone = COALESCE(contact_phone, ?),
                contact_username = COALESCE(contact_username, ?)
            WHERE order_id = ? AND user_id = ?
            """,
            (phone, username, order_id, user_id),
        )
        await db.commit()


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


async def fetch_reviews_page(db_path: Path, limit: int, offset: int) -> list[Review]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT *
            FROM reviews
            WHERE status IN ('submitted', 'declined')
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
            return [Review(dict(row)) for row in rows]


async def get_review(db_path: Path, review_id: str) -> Optional[Review]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)) as cursor:
            row = await cursor.fetchone()
            return Review(dict(row)) if row else None


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


# === Campaigns ===


async def create_campaign(
    db_path: Path,
    title: str,
    body: str,
    price_kopeks: int,
    interest_redirect: str,
) -> Campaign:
    campaign_id = str(uuid.uuid4())
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO campaigns (id, title, body, price_kopeks, interest_redirect)
            VALUES (?, ?, ?, ?, ?)
            """,
            (campaign_id, title, body, price_kopeks, interest_redirect),
        )
        await db.commit()
    return {
        "id": campaign_id,
        "title": title,
        "body": body,
        "price_kopeks": price_kopeks,
        "interest_redirect": interest_redirect,
    }


async def list_campaigns(db_path: Path) -> list[Campaign]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        base = "SELECT * FROM campaigns"
        base += " ORDER BY rowid DESC"
        async with db.execute(base) as cursor:
            rows = await cursor.fetchall()
            return [Campaign(dict(row)) for row in rows]


async def delete_campaign(db_path: Path, campaign_id: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "DELETE FROM campaign_responses WHERE campaign_id = ?",
            (campaign_id,),
        )
        await db.execute(
            "DELETE FROM campaign_audience WHERE campaign_id = ?",
            (campaign_id,),
        )
        await db.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
        await db.commit()


async def get_campaign(db_path: Path, campaign_id: str) -> Optional[Campaign]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)) as cursor:
            row = await cursor.fetchone()
            return Campaign(dict(row)) if row else None


async def fetch_paid_user_ids(db_path: Path) -> list[int]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT DISTINCT user_id
            FROM orders
            WHERE status = 'paid'
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [int(row[0]) for row in rows]


async def add_campaign_audience(db_path: Path, campaign_id: str, user_ids: list[int]) -> None:
    now = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.executemany(
            """
            INSERT OR IGNORE INTO campaign_audience (campaign_id, user_id, status, updated_at)
            VALUES (?, ?, 'pending', ?)
            """,
            [(campaign_id, user_id, now) for user_id in user_ids],
        )
        await db.commit()


async def update_campaign_audience_status(
    db_path: Path,
    campaign_id: str,
    user_id: int,
    status: str,
    *,
    message_id: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    now = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE campaign_audience
            SET status = ?,
                message_id = COALESCE(?, message_id),
                error = ?,
                updated_at = ?
            WHERE campaign_id = ? AND user_id = ?
            """,
            (status, message_id, error, now, campaign_id, user_id),
        )
        await db.commit()


async def get_campaign_audience(
    db_path: Path,
    campaign_id: str,
    *,
    statuses: Optional[list[str]] = None,
) -> list[CampaignAudience]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        base = "SELECT * FROM campaign_audience WHERE campaign_id = ?"
        params: list = [campaign_id]
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            base += f" AND status IN ({placeholders})"
            params.extend(statuses)
        base += " ORDER BY updated_at DESC"
        async with db.execute(base, tuple(params)) as cursor:
            rows = await cursor.fetchall()
            return [CampaignAudience(dict(row)) for row in rows]


async def campaign_has_audience(db_path: Path, campaign_id: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT 1 FROM campaign_audience WHERE campaign_id = ? LIMIT 1",
            (campaign_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def fetch_campaign_audience_stats(db_path: Path, campaign_id: str) -> dict[str, int]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT status, COUNT(*) AS cnt
            FROM campaign_audience
            WHERE campaign_id = ?
            GROUP BY status
            """,
            (campaign_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: int(row[1]) for row in rows}


async def create_or_update_campaign_response(
    db_path: Path,
    campaign_id: str,
    user_id: int,
    *,
    full_name: Optional[str] = None,
    birthdate: Optional[str] = None,
    phone: Optional[str] = None,
    raw_text: Optional[str] = None,
    status: Optional[str] = None,
) -> CampaignResponse:
    now = _now_iso()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM campaign_responses WHERE campaign_id = ? AND user_id = ?",
            (campaign_id, user_id),
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            response_id = existing["id"]
            await db.execute(
                """
                UPDATE campaign_responses
                SET full_name = COALESCE(?, full_name),
                    birthdate = COALESCE(?, birthdate),
                    phone = COALESCE(?, phone),
                    raw_text = COALESCE(?, raw_text),
                    status = COALESCE(?, status),
                    updated_at = ?
                WHERE id = ?
                """,
                (full_name, birthdate, phone, raw_text, status, now, response_id),
            )
        else:
            response_id = str(uuid.uuid4())
            await db.execute(
                """
                INSERT INTO campaign_responses (
                    id, campaign_id, user_id, full_name, birthdate, phone, raw_text, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    response_id,
                    campaign_id,
                    user_id,
                    full_name,
                    birthdate,
                    phone,
                    raw_text,
                    status or "collecting",
                    now,
                    now,
                ),
            )

        await db.commit()
        async with db.execute(
            "SELECT * FROM campaign_responses WHERE id = ?",
            (response_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return CampaignResponse(dict(row)) if row else {
                "id": response_id,
                "campaign_id": campaign_id,
                "user_id": user_id,
                "full_name": full_name,
                "birthdate": birthdate,
                "phone": phone,
                "raw_text": raw_text,
                "status": status or "collecting",
                "created_at": now,
                "updated_at": now,
            }


async def get_pending_campaign_response_for_user(
    db_path: Path,
    user_id: int,
) -> Optional[CampaignResponse]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT r.*
            FROM campaign_responses AS r
            JOIN campaign_audience AS a
                ON a.campaign_id = r.campaign_id AND a.user_id = r.user_id
            WHERE r.user_id = ? AND r.status IN ('collecting', 'waiting_contact')
            ORDER BY r.updated_at DESC
            LIMIT 1
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return CampaignResponse(dict(row)) if row else None


async def list_campaign_responses(
    db_path: Path,
    campaign_id: str,
) -> list[CampaignResponse]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT *
            FROM campaign_responses
            WHERE campaign_id = ?
            ORDER BY updated_at DESC
            """,
            (campaign_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            seen: set[int] = set()
            responses: list[CampaignResponse] = []
            for row in rows:
                resp = CampaignResponse(dict(row))
                if resp["user_id"] in seen:
                    continue
                seen.add(resp["user_id"])
                responses.append(resp)
            return responses

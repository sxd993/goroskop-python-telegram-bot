import secrets
import string
from typing import Optional

from app.services import db

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


def generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def build_referral_link(username: str | None, code: str) -> Optional[str]:
    if not username:
        return None
    return f"https://t.me/{username}?start=ref_{code}"


async def get_or_create_promocode(db_path, user_id: int):
    existing = await db.get_promocode_by_user(db_path, user_id)
    if existing:
        return existing
    for _ in range(10):
        code = generate_code()
        if await db.get_promocode_by_code(db_path, code):
            continue
        return await db.create_promocode(db_path, user_id, code)
    raise RuntimeError("Failed to generate unique promo code")

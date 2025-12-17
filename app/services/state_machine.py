import logging
from enum import StrEnum
from pathlib import Path
from typing import Optional

from app.models import User
from app.services import db

logger = logging.getLogger(__name__)

_KEEP = object()


class UserState(StrEnum):
    IDLE = "idle"
    ORDER_INITIATED = "order_initiated"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    DELIVERED = "delivered"
    REVIEW_PENDING = "review_pending"
    REVIEWED = "reviewed"


ALLOWED_TRANSITIONS: dict[UserState, set[UserState]] = {
    UserState.IDLE: {UserState.IDLE, UserState.ORDER_INITIATED},
    UserState.ORDER_INITIATED: {UserState.PAYMENT_PENDING, UserState.IDLE},
    UserState.PAYMENT_PENDING: {UserState.PAID, UserState.IDLE, UserState.PAYMENT_PENDING},
    UserState.PAID: {UserState.DELIVERED, UserState.PAYMENT_PENDING},
    UserState.DELIVERED: {UserState.REVIEW_PENDING},
    UserState.REVIEW_PENDING: {UserState.REVIEWED, UserState.IDLE},
    UserState.REVIEWED: {UserState.IDLE, UserState.ORDER_INITIATED},
}


class InvalidStateTransition(Exception):
    pass


async def _get_or_create_user(db_path: Path, user_id: int) -> User:
    user = await db.get_user(db_path, user_id)
    if user:
        return user
    created = await db.ensure_user(db_path, user_id, UserState.IDLE.value, None)
    logger.info("User created with default state idle user_id=%s", user_id)
    return created


async def _transition(
    db_path: Path,
    user_id: int,
    new_state: UserState,
    *,
    last_order_id: Optional[str] | object = _KEEP,
    force: bool = False,
) -> User:
    user = await _get_or_create_user(db_path, user_id)
    current_state = UserState(user["state"])
    keep_last_order = last_order_id is _KEEP
    if new_state == current_state and keep_last_order:
        return user
    if not force and new_state not in ALLOWED_TRANSITIONS.get(current_state, set()):
        raise InvalidStateTransition(
            f"Transition from {current_state.value} to {new_state.value} is not allowed"
        )
    next_order_id = user.get("last_order_id") if keep_last_order else last_order_id  # type: ignore[assignment]
    updated = await db.update_user_state(db_path, user_id, new_state.value, next_order_id)
    logger.info(
        "User state transition user_id=%s %s -> %s last_order_id=%s",
        user_id,
        current_state.value,
        new_state.value,
        next_order_id,
    )
    return updated


async def ensure_idle(db_path: Path, user_id: int) -> User:
    return await _transition(db_path, user_id, UserState.IDLE, last_order_id=None, force=True)


async def set_order_initiated(db_path: Path, user_id: int, order_id: str) -> User:
    return await _transition(db_path, user_id, UserState.ORDER_INITIATED, last_order_id=order_id)


async def set_payment_pending(db_path: Path, user_id: int, order_id: str) -> User:
    return await _transition(db_path, user_id, UserState.PAYMENT_PENDING, last_order_id=order_id)


async def set_paid(db_path: Path, user_id: int, order_id: str) -> User:
    return await _transition(db_path, user_id, UserState.PAID, last_order_id=order_id)


async def set_delivered(db_path: Path, user_id: int, order_id: str) -> User:
    return await _transition(db_path, user_id, UserState.DELIVERED, last_order_id=order_id)


async def set_review_pending(db_path: Path, user_id: int, order_id: str) -> User:
    return await _transition(db_path, user_id, UserState.REVIEW_PENDING, last_order_id=order_id)


async def set_reviewed(db_path: Path, user_id: int, order_id: Optional[str]) -> User:
    return await _transition(db_path, user_id, UserState.REVIEWED, last_order_id=order_id)


async def get_user_state(db_path: Path, user_id: int) -> UserState:
    user = await _get_or_create_user(db_path, user_id)
    try:
        return UserState(user["state"])
    except Exception:
        logger.warning("Unknown user state=%s user_id=%s, resetting to idle", user["state"], user_id)
        await ensure_idle(db_path, user_id)
        return UserState.IDLE

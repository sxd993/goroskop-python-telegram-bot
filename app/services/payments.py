import logging
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypedDict

from app.models import Payment
from app.services import db

logger = logging.getLogger(__name__)


class PaymentStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class PaymentResult(TypedDict):
    applied: bool
    reason: str
    payment: Payment


async def _log_duplicate(provider_tx_id: str, status: str) -> None:
    logger.info("Duplicate webhook provider_tx_id=%s status=%s", provider_tx_id, status)


async def handle_webhook(
    db_path: Path,
    order_id: str,
    provider_tx_id: str,
    status: Literal[PaymentStatus.SUCCESS, PaymentStatus.FAILED],
    amount_kopeks: int,
    currency: str,
    payload: str,
) -> PaymentResult:
    existing = await db.get_payment_by_provider_id(db_path, provider_tx_id)
    if existing:
        await _log_duplicate(provider_tx_id, existing["status"])
        reason = "duplicate_success" if existing["status"] == PaymentStatus.SUCCESS.value else "duplicate_failed"
        return {
            "applied": False,
            "reason": reason,
            "payment": existing,
        }

    payment = await db.create_payment(
        db_path,
        order_id=order_id,
        provider_tx_id=provider_tx_id,
        status=status.value,
        amount_kopeks=amount_kopeks,
        currency=currency,
        payload=payload,
    )
    if status == PaymentStatus.SUCCESS:
        await db.mark_paid(db_path, order_id, provider_tx_id)
    else:
        await db.mark_payment_failed(db_path, order_id)
    logger.info(
        "Payment recorded provider_tx_id=%s status=%s order_id=%s",
        provider_tx_id,
        status.value,
        order_id,
    )
    return {
        "applied": True,
        "reason": status.value,
        "payment": payment,
    }


async def handle_failed_webhook(
    db_path: Path,
    order_id: str,
    provider_tx_id: str,
    amount_kopeks: int,
    currency: str,
    payload: str,
) -> PaymentResult:
    existing = await db.get_payment_by_provider_id(db_path, provider_tx_id)
    if existing:
        await _log_duplicate(provider_tx_id, existing["status"])
        return {"applied": False, "reason": "duplicate", "payment": existing}

    payment = await db.create_payment(
        db_path,
        order_id=order_id,
        provider_tx_id=provider_tx_id,
        status=PaymentStatus.FAILED.value,
        amount_kopeks=amount_kopeks,
        currency=currency,
        payload=payload,
    )
    await db.mark_payment_failed(db_path, order_id)
    logger.warning(
        "Payment marked failed provider_tx_id=%s order_id=%s",
        provider_tx_id,
        order_id,
    )
    return {"applied": True, "reason": PaymentStatus.FAILED.value, "payment": payment}

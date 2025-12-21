import logging
from typing import Optional, Tuple

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.features import texts
from app.features.user.dependencies import get_db_path
from app.features.user.keyboards import (
    build_campaign_contact_keyboard,
    build_campaign_interest_keyboard,
)
from app.services import db

logger = logging.getLogger(__name__)

router = Router()


def _parse_user_text(text: str) -> Tuple[Optional[str], Optional[str]]:
    parts = [line.strip() for line in text.splitlines() if line.strip()]
    full_name = parts[0] if parts else None
    birthdate = parts[1] if len(parts) > 1 else None
    return full_name, birthdate


@router.callback_query(F.data.startswith("campaign:interest:"))
async def handle_campaign_interest(callback: CallbackQuery):
    campaign_id = (callback.data or "").split(":", maxsplit=2)[-1]
    db_path = get_db_path(callback.bot)
    campaign = await db.get_campaign(db_path, campaign_id)
    if not campaign:
        await callback.answer("Рассылка недоступна", show_alert=True)
        return
    await db.add_campaign_audience(db_path, campaign_id, [callback.from_user.id])
    await db.update_campaign_audience_status(db_path, campaign_id, callback.from_user.id, "interested")
    await db.create_or_update_campaign_response(db_path, campaign_id, callback.from_user.id, status="collecting")
    await callback.answer("Записал интерес")
    await callback.message.answer(
        texts.campaign_interest_prompt(),
        reply_markup=build_campaign_contact_keyboard(campaign_id),
    )


@router.callback_query(F.data.startswith("campaign:decline:"))
async def handle_campaign_decline(callback: CallbackQuery):
    campaign_id = (callback.data or "").split(":", maxsplit=2)[-1]
    db_path = get_db_path(callback.bot)
    campaign = await db.get_campaign(db_path, campaign_id)
    if not campaign:
        await callback.answer("Рассылка недоступна", show_alert=True)
        return
    await db.add_campaign_audience(db_path, campaign_id, [callback.from_user.id])
    await db.update_campaign_audience_status(db_path, campaign_id, callback.from_user.id, "declined")
    await callback.answer()
    await callback.message.answer(texts.campaign_declined())


@router.message(F.contact)
async def handle_campaign_contact(message: Message):
    db_path = get_db_path(message.bot)
    pending = await db.get_pending_campaign_response_for_user(db_path, message.from_user.id)
    if not pending:
        return
    await db.create_or_update_campaign_response(
        db_path,
        pending["campaign_id"],
        message.from_user.id,
        phone=message.contact.phone_number if message.contact else None,
        status="completed",
    )
    await db.update_campaign_audience_status(
        db_path,
        pending["campaign_id"],
        message.from_user.id,
        "interested",
    )
    await message.answer(texts.campaign_contact_saved())


@router.message(F.text)
async def handle_campaign_text(message: Message):
    if not message.text or message.text.startswith("/"):
        return
    db_path = get_db_path(message.bot)
    pending = await db.get_pending_campaign_response_for_user(db_path, message.from_user.id)
    if not pending:
        return
    full_name, birthdate = _parse_user_text(message.text)
    await db.create_or_update_campaign_response(
        db_path,
        pending["campaign_id"],
        message.from_user.id,
        full_name=full_name,
        birthdate=birthdate,
        raw_text=message.text.strip(),
        status="waiting_contact",
    )
    await message.answer(
        texts.campaign_interest_saved(),
        reply_markup=build_campaign_contact_keyboard(pending["campaign_id"]),
    )

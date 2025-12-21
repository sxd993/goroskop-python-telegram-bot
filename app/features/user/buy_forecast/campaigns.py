from datetime import datetime
from typing import Optional

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import texts
from app.features.user.dependencies import get_db_path
from app.features.user.keyboards import (
    build_campaign_contact_keyboard,
    build_campaign_interest_keyboard,
)
from app.features.user.buy_forecast.states import CampaignResponseFlow
from app.services import db

router = Router()


def _parse_birthdate(value: str) -> Optional[str]:
    try:
        parsed = datetime.strptime(value.strip(), "%d.%m.%Y")
    except ValueError:
        return None
    if parsed.year < 1900 or parsed > datetime.utcnow():
        return None
    return parsed.strftime("%d.%m.%Y")


@router.callback_query(F.data.startswith("campaign:interest:"))
async def handle_campaign_interest(callback: CallbackQuery, state: FSMContext):
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
    await state.clear()
    await state.update_data(campaign_id=campaign_id)
    await state.set_state(CampaignResponseFlow.fio)
    await callback.message.answer(texts.campaign_prompt_full_name())

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


@router.message(StateFilter(CampaignResponseFlow.fio), F.text)
async def handle_campaign_full_name(message: Message, state: FSMContext):
    if not message.text or message.text.startswith("/"):
        return
    data = await state.get_data()
    campaign_id = data.get("campaign_id")
    if not campaign_id:
        await state.clear()
        return

    db_path = get_db_path(message.bot)
    await db.create_or_update_campaign_response(
        db_path,
        campaign_id,
        message.from_user.id,
        full_name=message.text.strip(),
        status="collecting",
    )
    await state.set_state(CampaignResponseFlow.birthdate)
    await message.answer(texts.campaign_prompt_birthdate())


@router.message(StateFilter(CampaignResponseFlow.birthdate), F.text)
async def handle_campaign_birthdate(message: Message, state: FSMContext):
    if not message.text or message.text.startswith("/"):
        return
    data = await state.get_data()
    campaign_id = data.get("campaign_id")
    if not campaign_id:
        await state.clear()
        return

    birthdate = _parse_birthdate(message.text.strip())
    if not birthdate:
        await message.answer(texts.campaign_birthdate_invalid())
        return

    db_path = get_db_path(message.bot)
    await db.create_or_update_campaign_response(
        db_path,
        campaign_id,
        message.from_user.id,
        birthdate=birthdate,
        status="waiting_contact",
    )
    await state.set_state(CampaignResponseFlow.contact)
    await message.answer(
        texts.campaign_interest_saved(),
        reply_markup=build_campaign_contact_keyboard(campaign_id),
    )


@router.message(StateFilter(CampaignResponseFlow.contact), F.contact)
async def handle_campaign_contact_card(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else None
    await _finalize_campaign_contact(message, state, phone)


@router.message(StateFilter(CampaignResponseFlow.contact), F.text)
async def handle_campaign_contact_text(message: Message, state: FSMContext):
    if not message.text or message.text.startswith("/"):
        return
    await _finalize_campaign_contact(message, state, message.text.strip())


async def _finalize_campaign_contact(message: Message, state: FSMContext, phone: Optional[str]) -> None:
    if not phone:
        return
    db_path = get_db_path(message.bot)
    pending = await db.get_pending_campaign_response_for_user(db_path, message.from_user.id)
    if not pending:
        await state.clear()
        return

    await db.create_or_update_campaign_response(
        db_path,
        pending["campaign_id"],
        message.from_user.id,
        phone=phone,
        status="completed",
    )
    await db.update_campaign_audience_status(
        db_path,
        pending["campaign_id"],
        message.from_user.id,
        "interested",
    )
    await state.clear()
    await message.answer(texts.campaign_contact_saved())

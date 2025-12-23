from aiogram import F, Router
from aiogram.types import CallbackQuery

from app import texts
from app.features.user.dependencies import get_db_path
from app.services import db

router = Router()


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
    await callback.answer()
    if callback.message:
        redirect_text = campaign.get("interest_redirect") or ""
        await callback.message.answer(redirect_text or texts.campaign_interest_redirect())

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



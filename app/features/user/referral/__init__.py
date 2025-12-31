from aiogram import F, Router
from aiogram.types import Message

from app import texts
from app.menu_labels import REFERRAL_LABEL
from app.features.user.buy_forecast.menu import build_user_start_markup
from app.features.user.dependencies import ensure_user, get_db_path
from app.services import db
from app.services.promocodes import build_referral_link, get_or_create_promocode

router = Router()


@router.message(F.text.casefold() == REFERRAL_LABEL.casefold())
async def handle_referral_link(message: Message) -> None:
    if not message.from_user:
        return
    await ensure_user(message.bot, message.from_user.id)
    db_path = get_db_path(message.bot)
    promo = await get_or_create_promocode(db_path, message.from_user.id)
    me = await message.bot.get_me()
    link = build_referral_link(me.username, promo["code"]) if me.username else None
    await message.answer(
        texts.referral_link_message(promo["code"], link, promo["paid_referrals"]),
        reply_markup=build_user_start_markup(message),
    )

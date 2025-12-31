from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app import texts
from app.menu_labels import REFERRAL_LABEL
from app.features.user.keyboards import build_referral_menu_keyboard
from app.features.user.dependencies import ensure_user, get_db_path
from app.services.promocodes import build_referral_link, get_or_create_promocode

router = Router()


@router.message(F.text.casefold() == REFERRAL_LABEL.casefold())
async def handle_referral_link(message: Message) -> None:
    if not message.from_user:
        return
    await message.answer(
        texts.referral_menu(),
        reply_markup=build_referral_menu_keyboard(),
    )


@router.callback_query(F.data == "referral:link")
async def handle_referral_link_button(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    await callback.answer()
    await ensure_user(callback.bot, callback.from_user.id)
    db_path = get_db_path(callback.bot)
    promo = await get_or_create_promocode(db_path, callback.from_user.id)
    me = await callback.bot.get_me()
    link = build_referral_link(me.username, promo["code"]) if me.username else None
    await callback.message.answer(texts.referral_link_only_message(link))


@router.callback_query(F.data == "referral:code")
async def handle_referral_code_button(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    await callback.answer()
    await ensure_user(callback.bot, callback.from_user.id)
    db_path = get_db_path(callback.bot)
    promo = await get_or_create_promocode(db_path, callback.from_user.id)
    await callback.message.answer(texts.referral_code_only_message(promo["code"]))


@router.callback_query(F.data == "referral:stats")
async def handle_referral_stats_button(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    await callback.answer()
    await ensure_user(callback.bot, callback.from_user.id)
    db_path = get_db_path(callback.bot)
    promo = await get_or_create_promocode(db_path, callback.from_user.id)
    await callback.message.answer(texts.referral_stats_message(promo["paid_referrals"]))

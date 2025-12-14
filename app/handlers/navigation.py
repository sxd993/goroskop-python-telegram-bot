import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app.config import Settings, SIGNS_RU
from app.keyboards.navigation import (
    build_months_keyboard,
    build_pay_keyboard,
    build_signs_keyboard,
    build_years_keyboard,
)
from app.models import Order
from app.services import db, media
from app.services.messaging import send_content
from app.services.parsing import (
    parse_month_data,
    parse_pay_data,
    parse_product,
    parse_sign_data,
    parse_year_data,
)
from app import texts

logger = logging.getLogger(__name__)

router = Router()

_settings: Settings | None = None


def setup_handlers(settings: Settings) -> None:
    global _settings
    _settings = settings


def get_settings(bot: Bot) -> Settings:
    if _settings is None:
        raise RuntimeError("Handlers are not configured with settings")
    return _settings


def get_db_path(bot: Bot) -> Path:
    return get_settings(bot).db_path


@router.message(Command("start"))
async def handle_start(message: Message):
    settings = get_settings(message.bot)
    years = media.available_years(settings.media_dir)
    if not years:
        await message.answer(texts.no_content())
        return
    keyboard = build_years_keyboard(years)
    await message.answer(texts.choose_year(), reply_markup=keyboard)


@router.callback_query(F.data.startswith("year:"))
async def handle_year(callback: CallbackQuery):
    year = parse_year_data(callback.data or "")
    await callback.answer()
    if not year:
        await callback.message.answer(texts.invalid_year())
        return
    settings = get_settings(callback.bot)
    years = media.available_years(settings.media_dir)
    if year not in years:
        await callback.message.answer(texts.year_unavailable())
        return
    months = media.months_for_year(settings.media_dir, year)
    if not months:
        await callback.message.answer(texts.months_missing())
        return
    keyboard = build_months_keyboard(settings.media_dir, year)
    await callback.message.answer(texts.year_prompt(year), reply_markup=keyboard)


@router.callback_query(F.data.startswith("month:"))
async def handle_month(callback: CallbackQuery):
    ym = parse_month_data(callback.data or "")
    await callback.answer()
    if not ym:
        await callback.message.answer(texts.invalid_month())
        return
    year = ym.split("-")[0]
    settings = get_settings(callback.bot)
    media_dir = settings.media_dir
    if year not in media.available_years(media_dir):
        await callback.message.answer(texts.year_unavailable())
        return
    if ym not in media.months_for_year(media_dir, year):
        await callback.message.answer(texts.month_unavailable())
        return
    signs = media.available_signs(media_dir, ym)
    if not signs:
        await callback.message.answer(texts.month_content_missing())
        return
    keyboard = build_signs_keyboard(media_dir, ym)
    month_name = media.month_name_from_ym(ym) or "Месяц"
    await callback.message.answer(texts.month_prompt(month_name, year), reply_markup=keyboard)


@router.callback_query(F.data.startswith("sign:"))
async def handle_sign(callback: CallbackQuery):
    parsed = parse_sign_data(callback.data or "")
    await callback.answer()
    if not parsed:
        await callback.message.answer(texts.invalid_sign())
        return
    ym, sign = parsed
    year = ym.split("-")[0]
    settings = get_settings(callback.bot)
    media_dir = settings.media_dir
    if year not in media.available_years(media_dir):
        await callback.message.answer(texts.year_unavailable())
        return
    if ym not in media.months_for_year(media_dir, year):
        await callback.message.answer(texts.month_unavailable())
        return
    if sign not in media.available_signs(media_dir, ym):
        await callback.message.answer(texts.sign_unavailable())
        return
    content_path = media.find_content_path(media_dir, ym, sign)
    if not content_path:
        await callback.message.answer(texts.content_missing())
        return
    product_id = media.build_product_id(ym, sign)
    if not product_id:
        await callback.message.answer(texts.invalid_product())
        return
    order = await db.create_order(
        settings.db_path,
        callback.from_user.id,
        product_id,
        settings.price_kopeks,
        settings.currency,
    )
    logger.info("Order created user=%s order_id=%s", callback.from_user.id, order["id"])
    month_name = media.month_name_from_ym(ym) or ym
    price_rub = settings.price_kopeks / 100
    text = texts.price_caption(month_name, ym.split("-")[0], sign, price_rub)
    await callback.message.answer(text, reply_markup=build_pay_keyboard(order["id"]))


async def send_invoice(callback: CallbackQuery, order: Order) -> None:
    settings = get_settings(callback.bot)
    parsed = parse_product(order["product_id"])
    if not parsed:
        await callback.message.answer(texts.invalid_product())
        return
    ym, sign = parsed
    month_name = media.month_name_from_ym(ym) or ym
    sign_name = SIGNS_RU.get(sign, sign)
    title = f"{month_name} {ym.split('-')[0]}"
    description = f"Гороскоп для знака {sign_name}"
    prices = [LabeledPrice(label="Гороскоп", amount=settings.price_kopeks)]
    await callback.message.answer_invoice(
        title=title,
        description=description,
        payload=order["id"],
        provider_token=settings.provider_token,
        currency=settings.currency,
        prices=prices,
    )
    logger.info("Invoice sent user=%s order_id=%s", callback.from_user.id, order["id"])
    await db.mark_invoice_sent(settings.db_path, order["id"])


@router.callback_query(F.data.startswith("pay:"))
async def handle_pay(callback: CallbackQuery):
    order_id = parse_pay_data(callback.data or "")
    await callback.answer()
    if not order_id:
        await callback.message.answer(texts.invalid_order())
        return
    settings = get_settings(callback.bot)
    order = await db.get_order(settings.db_path, order_id)
    if not order or order["user_id"] != callback.from_user.id:
        await callback.message.answer(texts.order_not_found())
        return
    parsed = parse_product(order["product_id"])
    if not parsed:
        await callback.message.answer(texts.invalid_product())
        return
    ym, sign = parsed
    media_dir = settings.media_dir
    if ym not in media.months_for_year(media_dir, ym.split("-")[0]) or sign not in media.available_signs(media_dir, ym):
        await callback.message.answer(texts.content_missing())
        return
    content_path = media.find_content_path(media_dir, ym, sign)
    if not content_path:
        await callback.message.answer(texts.content_missing())
        return
    if order["status"] == "paid":
        await callback.message.answer(texts.order_paid_message())
        await deliver_file(callback.bot, callback.message.chat.id, order, content_path)
        return
    await send_invoice(callback, order)


@router.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery):
    settings = get_settings(query.bot)
    order = await db.get_order(settings.db_path, query.invoice_payload)
    if not order or order["user_id"] != query.from_user.id or order["status"] == "paid":
        await query.answer(ok=False, error_message="Заказ недоступен.")
        logger.info("Pre-checkout rejected user=%s order_id=%s", query.from_user.id, query.invoice_payload)
        return
    await query.answer(ok=True)
    logger.info("Pre-checkout ok user=%s order_id=%s", query.from_user.id, order["id"])


async def deliver_file(bot: Bot, chat_id: int, order: Order, content_path: Path) -> None:
    parsed = parse_product(order["product_id"])
    if not parsed:
        await bot.send_message(chat_id, texts.invalid_product())
        return
    ym, sign = parsed
    month_name = media.month_name_from_ym(ym) or ym
    sign_name = SIGNS_RU.get(sign, sign)
    caption = f"{month_name} {ym.split('-')[0]}, {sign_name}"
    delivered = await send_content(bot, chat_id, content_path, caption)
    if delivered:
        await db.mark_delivered(get_db_path(bot), order["id"])
        logger.info("Content sent user=%s order_id=%s", chat_id, order["id"])


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message):
    payment = message.successful_payment
    order_id = payment.invoice_payload
    settings = get_settings(message.bot)
    order = await db.get_order(settings.db_path, order_id)
    if not order or order["user_id"] != message.from_user.id:
        await message.answer(texts.order_not_found())
        return
    try:
        await db.mark_paid(settings.db_path, order_id, payment.telegram_payment_charge_id)
        logger.info(
            "Payment successful user=%s order_id=%s charge_id=%s",
            message.from_user.id,
            order_id,
            payment.telegram_payment_charge_id,
        )
    except Exception:
        logger.exception("Failed to mark paid order_id=%s", order_id)
    parsed = parse_product(order["product_id"])
    if not parsed:
        await message.answer(texts.invalid_product())
        return
    ym, sign = parsed
    content_path = media.find_content_path(settings.media_dir, ym, sign)
    if not content_path:
        await message.answer(texts.file_missing_after_pay())
        return
    await deliver_file(message.bot, message.chat.id, order, content_path)

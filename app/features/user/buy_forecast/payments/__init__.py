import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app import texts
from app.config import SIGNS_RU
from app.features.user.dependencies import ensure_user, get_db_path, get_settings
from app.features.user.keyboards import build_review_cancel_keyboard
from ..reviews import prompt_review
from app.services import db, media, payments, state_machine
from app.services.messaging import send_content, send_message_safe
from app.services.payments import PaymentStatus
from app.services.pricing import get_price_kopeks
from app.services.parsing import (
    parse_invoice_payload,
    parse_pay_data,
    parse_product,
)
from app.services.state_machine import InvalidStateTransition, UserState

logger = logging.getLogger(__name__)

router = Router()


def _build_invoice_title_description(parsed: dict) -> tuple[str, str]:
    sign_name = SIGNS_RU.get(parsed["sign"], parsed["sign"])
    if parsed["kind"] == "month" and parsed["month"]:
        ym = f"{parsed['year']}-{parsed['month']}"
        month_name = media.month_name_from_ym(ym) or ym
        title = f"{month_name} {parsed['year']}"
        description = f"Гороскоп {month_name.lower()} для знака {sign_name}"
    else:
        title = f"{parsed['year']} год"
        description = f"Годовой гороскоп для знака {sign_name}"
    return title, description


async def send_invoice(callback: CallbackQuery, product_id: str, order_id: str) -> None:
    settings = get_settings(callback.bot)
    parsed = parse_product(product_id)
    if not parsed:
        await callback.message.answer(texts.invalid_product())
        return
    title, description = _build_invoice_title_description(parsed)
    amount_kopeks = get_price_kopeks(parsed["kind"], pricing_path=settings.pricing_path)
    prices = [LabeledPrice(label="Гороскоп", amount=amount_kopeks)]
    payload = f"{product_id}|{callback.from_user.id}|{order_id}"
    await callback.message.answer_invoice(
        title=title,
        description=description,
        payload=payload,
        provider_token=settings.provider_token,
        currency=settings.currency,
        prices=prices,
    )
    logger.info("Invoice sent user=%s payload=%s", callback.from_user.id, payload)


@router.callback_query(F.data.startswith("pay:"))
async def handle_pay(callback: CallbackQuery):
    product_id = parse_pay_data(callback.data or "")
    await callback.answer()
    if not product_id:
        await callback.message.answer(texts.invalid_product())
        return
    parsed = parse_product(product_id)
    if not parsed:
        await callback.message.answer(texts.invalid_product())
        return
    settings = get_settings(callback.bot)
    media_dir = settings.media_dir
    db_path = get_db_path(callback.bot)
    await ensure_user(callback.bot, callback.from_user.id)
    user_state = await state_machine.get_user_state(db_path, callback.from_user.id)
    if user_state == UserState.REVIEW_PENDING:
        await callback.message.answer(texts.review_request(), reply_markup=build_review_cancel_keyboard())
        return
    content_path: Path | None = None
    if parsed["kind"] == "month" and parsed["month"]:
        ym = f"{parsed['year']}-{parsed['month']}"
        if ym not in media.months_for_year(media_dir, parsed["year"]) or parsed["sign"] not in media.available_month_signs(media_dir, ym):
            await callback.message.answer(texts.content_missing())
            return
        content_path = media.find_month_content_path(media_dir, ym, parsed["sign"])
    else:
        if parsed["year"] not in media.available_yearly_years(media_dir) or parsed["sign"] not in media.available_year_signs(media_dir, parsed["year"]):
            await callback.message.answer(texts.content_missing())
            return
        content_path = media.find_year_content_path(media_dir, parsed["year"], parsed["sign"])
    if not content_path:
        await callback.message.answer(texts.content_missing())
        return
    amount_kopeks = get_price_kopeks(parsed["kind"], pricing_path=settings.pricing_path)
    order = await db.create_order(db_path, callback.from_user.id, product_id, amount_kopeks, settings.currency)
    try:
        await state_machine.set_order_initiated(db_path, callback.from_user.id, order["id"])
    except InvalidStateTransition:
        logger.warning("Order initiation rejected by state machine user_id=%s", callback.from_user.id)
        await send_message_safe(callback.bot, callback.message.chat.id, texts.temporary_error())
        return
    try:
        await send_invoice(callback, product_id, order["id"])
    except Exception:
        logger.exception("Failed to send invoice order_id=%s user_id=%s", order["id"], callback.from_user.id)
        await state_machine.ensure_idle(db_path, callback.from_user.id)
        await send_message_safe(callback.bot, callback.message.chat.id, texts.temporary_error())
        return
    await db.mark_invoice_sent(db_path, order["id"])
    try:
        await state_machine.set_payment_pending(db_path, callback.from_user.id, order["id"])
    except InvalidStateTransition:
        logger.warning("Payment pending transition rejected user_id=%s order_id=%s", callback.from_user.id, order["id"])
        await send_message_safe(callback.bot, callback.message.chat.id, texts.temporary_error())
        await state_machine.ensure_idle(db_path, callback.from_user.id)


@router.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery):
    parsed = parse_invoice_payload(query.invoice_payload)
    if not parsed:
        await query.answer(ok=False, error_message="Заказ недоступен.")
        logger.info("Pre-checkout rejected user=%s payload=%s", query.from_user.id, query.invoice_payload)
        return
    product, user_id, order_id = parsed
    if user_id != query.from_user.id:
        await query.answer(ok=False, error_message="Заказ недоступен.")
        logger.info("Pre-checkout rejected user mismatch=%s payload=%s", query.from_user.id, query.invoice_payload)
        return
    if not order_id:
        await query.answer(ok=False, error_message="Заказ недоступен.")
        logger.info("Pre-checkout rejected order missing user=%s payload=%s", query.from_user.id, query.invoice_payload)
        return
    order = await db.get_order(get_db_path(query.bot), order_id)
    if not order or order["user_id"] != query.from_user.id:
        await query.answer(ok=False, error_message="Заказ недоступен.")
        logger.info("Pre-checkout rejected order not found user=%s payload=%s", query.from_user.id, query.invoice_payload)
        return
    product_id = (
        media.build_month_product_id(f"{product['year']}-{product['month']}", product["sign"])
        if product["kind"] == "month" and product["month"]
        else media.build_year_product_id(product["year"], product["sign"])
    )
    if not product_id or order["product_id"] != product_id:
        await query.answer(ok=False, error_message="Заказ недоступен.")
        logger.info("Pre-checkout rejected order mismatch user=%s payload=%s", query.from_user.id, query.invoice_payload)
        return
    settings = get_settings(query.bot)
    media_dir = settings.media_dir
    exists = False
    if product["kind"] == "month" and product["month"]:
        ym = f"{product['year']}-{product['month']}"
        exists = (
            ym in media.months_for_year(media_dir, product["year"])
            and product["sign"] in media.available_month_signs(media_dir, ym)
            and media.find_month_content_path(media_dir, ym, product["sign"]) is not None
        )
    else:
        exists = (
            product["year"] in media.available_yearly_years(media_dir)
            and product["sign"] in media.available_year_signs(media_dir, product["year"])
            and media.find_year_content_path(media_dir, product["year"], product["sign"]) is not None
        )
    if not exists:
        await query.answer(ok=False, error_message="Контент недоступен.")
        logger.info("Pre-checkout rejected content missing user=%s payload=%s", query.from_user.id, query.invoice_payload)
        return
    await query.answer(ok=True)
    logger.info("Pre-checkout ok user=%s payload=%s", query.from_user.id, query.invoice_payload)


async def deliver_file(bot: Bot, chat_id: int, order: dict, content_path: Path) -> bool:
    db_path = get_db_path(bot)
    user_id = order.get("user_id", chat_id)
    if order.get("delivered_at"):
        logger.info("Order already delivered user=%s order_id=%s", user_id, order["id"])
        return True
    parsed = parse_product(order["product_id"])
    if not parsed:
        await bot.send_message(chat_id, texts.invalid_product())
        return False
    sign_name = SIGNS_RU.get(parsed["sign"], parsed["sign"])
    if parsed["kind"] == "month" and parsed["month"]:
        ym = f"{parsed['year']}-{parsed['month']}"
        month_name = media.month_name_from_ym(ym) or ym
        caption = f"{month_name} {parsed['year']}, {sign_name}"
    else:
        caption = f"{parsed['year']} год, {sign_name}"
    delivered = await send_content(bot, chat_id, content_path, caption)
    if delivered:
        await db.mark_delivered(db_path, order["id"])
        try:
            await state_machine.set_delivered(db_path, user_id, order["id"])
            await state_machine.set_review_pending(db_path, user_id, order["id"])
        except InvalidStateTransition:
            logger.warning("Cannot move user to delivered/review_pending user_id=%s", user_id)
        logger.info("Content sent user=%s order_id=%s", user_id, order["id"])
        await prompt_review(bot, chat_id, order)
    else:
        await send_message_safe(bot, chat_id, texts.temporary_error())
    return delivered


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    parsed_payload = parse_invoice_payload(payload)
    if not parsed_payload:
        await message.answer(texts.invalid_product())
        return
    product, user_id, order_id = parsed_payload
    if user_id != message.from_user.id:
        await message.answer(texts.order_not_found())
        return
    await ensure_user(message.bot, message.from_user.id)
    if not order_id:
        await message.answer(texts.order_not_found())
        return
    db_path = get_db_path(message.bot)
    order = await db.get_order(db_path, order_id)
    if not order or order["user_id"] != message.from_user.id:
        await message.answer(texts.order_not_found())
        return
    settings = get_settings(message.bot)
    media_dir = settings.media_dir
    content_path: Path | None = None
    if product["kind"] == "month" and product["month"]:
        ym = f"{product['year']}-{product['month']}"
        content_path = media.find_month_content_path(media_dir, ym, product["sign"])
    else:
        content_path = media.find_year_content_path(media_dir, product["year"], product["sign"])
    if not content_path:
        await message.answer(texts.file_missing_after_pay())
        return
    product_id = (
        media.build_month_product_id(f"{product['year']}-{product['month']}", product["sign"])
        if product["kind"] == "month" and product["month"]
        else media.build_year_product_id(product["year"], product["sign"])
    )
    if not product_id or order["product_id"] != product_id:
        await message.answer(texts.invalid_product())
        return
    result = await payments.handle_webhook(
        db_path,
        order_id=order_id,
        provider_tx_id=payment.telegram_payment_charge_id,
        status=PaymentStatus.SUCCESS,
        amount_kopeks=payment.total_amount,
        currency=payment.currency,
        payload=payload,
    )
    if not result["applied"]:
        if result["payment"]["status"] == PaymentStatus.FAILED.value:
            await message.answer(texts.payment_failed())
            return
        await message.answer(texts.payment_duplicate())
        order = await db.get_order(db_path, order_id) or order
        if order.get("delivered_at"):
            return
        if order.get("status") != "paid":
            return
    else:
        try:
            await state_machine.set_paid(db_path, message.from_user.id, order_id)
        except InvalidStateTransition:
            logger.warning("Unexpected paid transition user_id=%s order_id=%s", message.from_user.id, order_id)
    order = await db.get_order(db_path, order_id) or order
    logger.info(
        "Payment successful user=%s order_id=%s payload=%s charge_id=%s",
        message.from_user.id,
        order_id,
        payload,
        payment.telegram_payment_charge_id,
    )
    await message.answer(texts.payment_success())
    await deliver_file(message.bot, message.chat.id, order, content_path)

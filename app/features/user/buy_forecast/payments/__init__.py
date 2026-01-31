import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app import texts
from app.config import SIGNS_RU
from app.features.user.dependencies import ensure_user, get_db_path, get_settings
from app.features.user.keyboards import (
    build_referral_prompt_keyboard,
    build_referral_skip_keyboard,
    build_review_cancel_keyboard,
)
from ..reviews import prompt_review
from app.services import db, media, payments, state_machine
from app.services.messaging import send_contents, send_message_safe
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


def _parse_referral_callback(data: str) -> tuple[str, str] | None:
    parts = data.split(":", maxsplit=2)
    if len(parts) != 3 or parts[0] != "referral":
        return None
    return parts[1], parts[2]


async def send_invoice(
    message: Message,
    user_id: int,
    product_id: str,
    order_id: str,
    amount_kopeks: int,
) -> None:
    settings = get_settings(message.bot)
    parsed = parse_product(product_id)
    if not parsed:
        await message.answer(texts.invalid_product())
        return
    title, description = _build_invoice_title_description(parsed)
    prices = [LabeledPrice(label="Гороскоп", amount=amount_kopeks)]
    payload = f"{product_id}|{user_id}|{order_id}"
    await message.answer_invoice(
        title=title,
        description=description,
        payload=payload,
        provider_token=settings.provider_token,
        currency=settings.currency,
        prices=prices,
    )
    logger.info("Invoice sent user=%s payload=%s", user_id, payload)


async def _start_payment_for_order(message: Message, *, product_id: str, order_id: str, user_id: int) -> None:
    db_path = get_db_path(message.bot)
    parsed = parse_product(product_id)
    if not parsed:
        await message.answer(texts.invalid_product())
        return
    promo_use = await db.get_promocode_use(db_path, order_id)
    apply_promo = bool(promo_use and promo_use["status"] == "pending" and promo_use["promo_code"])
    ym = None
    if parsed["kind"] == "month" and parsed["month"]:
        ym = f"{parsed['year']}-{parsed['month']}"
    amount_kopeks = get_price_kopeks(
        parsed["kind"],
        pricing_path=get_settings(message.bot).pricing_path,
        ym=ym,
        apply_promo=apply_promo,
    )
    order = await db.get_order(db_path, order_id)
    if order and order.get("amount_kopeks") != amount_kopeks:
        await db.update_order_amount(db_path, order_id, amount_kopeks)
    try:
        await send_invoice(message, user_id, product_id, order_id, amount_kopeks)
    except Exception:
        logger.exception("Failed to send invoice order_id=%s user_id=%s", order_id, user_id)
        await state_machine.ensure_idle(db_path, user_id)
        await send_message_safe(message.bot, message.chat.id, texts.temporary_error())
        return
    await db.mark_invoice_sent(db_path, order_id)
    try:
        await state_machine.set_payment_pending(db_path, user_id, order_id)
    except InvalidStateTransition:
        logger.warning("Payment pending transition rejected user_id=%s order_id=%s", user_id, order_id)
        await send_message_safe(message.bot, message.chat.id, texts.temporary_error())
        await state_machine.ensure_idle(db_path, user_id)


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
    content_paths: list[Path] = []
    if parsed["kind"] == "month" and parsed["month"]:
        ym = f"{parsed['year']}-{parsed['month']}"
        if ym not in media.months_for_year(media_dir, parsed["year"]) or parsed["sign"] not in media.available_month_signs(media_dir, ym):
            await callback.message.answer(texts.content_missing())
            return
        content_paths = media.find_month_content_paths(media_dir, ym, parsed["sign"])
    else:
        if parsed["year"] not in media.available_yearly_years(media_dir) or parsed["sign"] not in media.available_year_signs(media_dir, parsed["year"]):
            await callback.message.answer(texts.content_missing())
            return
        content_paths = media.find_year_content_paths(media_dir, parsed["year"], parsed["sign"])
    if not content_paths:
        await callback.message.answer(texts.content_missing())
        return
    ym = None
    if parsed["kind"] == "month" and parsed["month"]:
        ym = f"{parsed['year']}-{parsed['month']}"
    amount_kopeks = get_price_kopeks(parsed["kind"], pricing_path=settings.pricing_path, ym=ym)
    order = await db.create_order(db_path, callback.from_user.id, product_id, amount_kopeks, settings.currency)
    try:
        await state_machine.set_order_initiated(db_path, callback.from_user.id, order["id"])
    except InvalidStateTransition:
        user = await db.get_user(db_path, callback.from_user.id)
        logger.warning(
            "Order initiation rejected by state machine user_id=%s state=%s last_order_id=%s",
            callback.from_user.id,
            user["state"] if user else None,
            user.get("last_order_id") if user else None,
        )
        await state_machine.ensure_idle(db_path, callback.from_user.id)
        try:
            await state_machine.set_order_initiated(db_path, callback.from_user.id, order["id"])
        except InvalidStateTransition:
            logger.warning(
                "Order initiation still rejected after reset user_id=%s order_id=%s",
                callback.from_user.id,
                order["id"],
            )
            await send_message_safe(callback.bot, callback.message.chat.id, texts.temporary_error())
            return
    intent = await db.get_promocode_intent(db_path, callback.from_user.id)
    if intent:
        await db.delete_promocode_intent(db_path, callback.from_user.id)
        if await db.has_applied_promocode_use(db_path, callback.from_user.id):
            await callback.message.answer(texts.referral_code_already_used())
        else:
            await db.create_promocode_use(
                db_path,
                order["id"],
                callback.from_user.id,
                "pending",
                promo_code=intent["promo_code"],
                referrer_user_id=intent["referrer_user_id"],
            )
            await callback.message.answer(texts.referral_code_saved())
        await _start_payment_for_order(
            callback.message,
            product_id=order["product_id"],
            order_id=order["id"],
            user_id=callback.from_user.id,
        )
        return
    await db.clear_promocode_uses_for_user(
        db_path,
        callback.from_user.id,
        statuses=["awaiting_code", "pending"],
    )
    await callback.message.answer(
        texts.referral_prompt(),
        reply_markup=build_referral_prompt_keyboard(order["id"]),
    )


@router.callback_query(F.data.startswith("referral:"))
async def handle_referral_prompt(callback: CallbackQuery):
    parsed = _parse_referral_callback(callback.data or "")
    await callback.answer()
    if not parsed:
        await callback.message.answer(texts.invalid_choice())
        return
    action, order_id = parsed
    db_path = get_db_path(callback.bot)
    order = await db.get_order(db_path, order_id)
    if not order or order["user_id"] != callback.from_user.id:
        await callback.message.answer(texts.order_not_found())
        return
    if action == "no":
        await db.delete_promocode_use(db_path, order_id)
        await _start_payment_for_order(
            callback.message,
            product_id=order["product_id"],
            order_id=order_id,
            user_id=callback.from_user.id,
        )
        return
    if action == "yes":
        await db.create_promocode_use(db_path, order_id, callback.from_user.id, "awaiting_code")
        await callback.message.answer(
            texts.referral_code_request(),
            reply_markup=build_referral_skip_keyboard(order_id),
        )
        return
    if action == "skip":
        await db.delete_promocode_use(db_path, order_id)
        await _start_payment_for_order(
            callback.message,
            product_id=order["product_id"],
            order_id=order_id,
            user_id=callback.from_user.id,
        )
        return
    await callback.message.answer(texts.invalid_choice())


@router.message(F.text)
async def handle_referral_code(message: Message):
    if not message.from_user:
        raise SkipHandler()
    db_path = get_db_path(message.bot)
    pending = await db.get_promocode_use_for_user(db_path, message.from_user.id, "awaiting_code")
    if not pending:
        raise SkipHandler()
    order = await db.get_order(db_path, pending["order_id"])
    if not order or order["user_id"] != message.from_user.id:
        await db.delete_promocode_use(db_path, pending["order_id"])
        await message.answer(texts.order_not_found())
        return
    if await db.has_applied_promocode_use(db_path, message.from_user.id):
        await db.delete_promocode_use(db_path, pending["order_id"])
        await message.answer(texts.referral_code_already_used())
        await _start_payment_for_order(
            message,
            product_id=order["product_id"],
            order_id=order["id"],
            user_id=message.from_user.id,
        )
        return
    code = (message.text or "").strip().upper()
    if not code:
        await message.answer(
            texts.referral_code_invalid(),
            reply_markup=build_referral_skip_keyboard(pending["order_id"]),
        )
        return
    promo = await db.get_promocode_by_code(db_path, code)
    if not promo:
        await message.answer(
            texts.referral_code_invalid(),
            reply_markup=build_referral_skip_keyboard(pending["order_id"]),
        )
        return
    if promo["user_id"] == message.from_user.id:
        await message.answer(
            texts.referral_code_self(),
            reply_markup=build_referral_skip_keyboard(pending["order_id"]),
        )
        return
    await db.update_promocode_use(
        db_path,
        pending["order_id"],
        promo_code=promo["code"],
        referrer_user_id=promo["user_id"],
        status="pending",
    )
    await _start_payment_for_order(
        message,
        product_id=order["product_id"],
        order_id=order["id"],
        user_id=message.from_user.id,
    )


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
            and bool(media.find_month_content_paths(media_dir, ym, product["sign"]))
        )
    else:
        exists = (
            product["year"] in media.available_yearly_years(media_dir)
            and product["sign"] in media.available_year_signs(media_dir, product["year"])
            and bool(media.find_year_content_paths(media_dir, product["year"], product["sign"]))
        )
    if not exists:
        await query.answer(ok=False, error_message="Контент недоступен.")
        logger.info("Pre-checkout rejected content missing user=%s payload=%s", query.from_user.id, query.invoice_payload)
        return
    await query.answer(ok=True)
    logger.info("Pre-checkout ok user=%s payload=%s", query.from_user.id, query.invoice_payload)


async def deliver_file(bot: Bot, chat_id: int, order: dict, content_paths: list[Path]) -> bool:
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
    delivered = await send_contents(bot, chat_id, content_paths, caption)
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
    content_paths: list[Path] = []
    if product["kind"] == "month" and product["month"]:
        ym = f"{product['year']}-{product['month']}"
        content_paths = media.find_month_content_paths(media_dir, ym, product["sign"])
    else:
        content_paths = media.find_year_content_paths(media_dir, product["year"], product["sign"])
    if not content_paths:
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
    applied_referral = False
    if order.get("status") == "paid":
        applied_referral = await db.apply_promocode_use(db_path, order_id)
    if applied_referral:
        logger.info("Referral applied order_id=%s", order_id)
    logger.info(
        "Payment successful user=%s order_id=%s payload=%s charge_id=%s",
        message.from_user.id,
        order_id,
        payload,
        payment.telegram_payment_charge_id,
    )
    await message.answer(texts.payment_success())
    await deliver_file(message.bot, message.chat.id, order, content_paths)

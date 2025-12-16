import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery, ForceReply

from app.config import Settings, SIGNS_RU
from app.features.user.keyboards import (
    build_layout_keyboard,
    build_month_signs_keyboard,
    build_months_keyboard,
    build_pay_keyboard,
    build_review_keyboard,
    build_year_signs_keyboard,
    build_years_keyboard,
)
from app.models import Order
from app.services import db, media
from app.services.messaging import send_content
from app.services.parsing import (
    parse_layout_choice,
    parse_month_data,
    parse_month_sign_data,
    parse_month_year_data,
    parse_pay_data,
    parse_product,
    parse_invoice_payload,
    parse_year_data,
    parse_year_sign_data,
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


async def _edit_or_send(message: Message, text: str, reply_markup):
    """
    Try to keep навигацию в одном окне: редактируем текущее сообщение, при ошибке шлем новое.
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        await message.answer(text, reply_markup=reply_markup)


@router.message(Command("start"))
async def handle_start(message: Message):
    settings = get_settings(message.bot)
    year_years = media.available_yearly_years(settings.media_dir)
    month_years = media.available_monthly_years(settings.media_dir)
    if not year_years and not month_years:
        await message.answer(texts.no_content())
        return
    keyboard = build_layout_keyboard(has_year=bool(year_years), has_month=bool(month_years))
    await message.answer(texts.welcome(), reply_markup=keyboard)


@router.callback_query(F.data.startswith("mode:"))
async def handle_mode(callback: CallbackQuery):
    mode = parse_layout_choice(callback.data or "")
    await callback.answer()
    settings = get_settings(callback.bot)
    year_years = media.available_yearly_years(settings.media_dir)
    month_years = media.available_monthly_years(settings.media_dir)
    if mode == "year":
        if not year_years:
            await callback.message.answer(texts.year_section_empty())
            return
        keyboard = build_years_keyboard(year_years, prefix="y-year", back="back:mode")
        await _edit_or_send(callback.message, texts.choose_yearly_year(), reply_markup=keyboard)
        return
    if mode == "month":
        if not month_years:
            await callback.message.answer(texts.month_section_empty())
            return
        keyboard = build_years_keyboard(month_years, prefix="m-year", back="back:mode")
        await _edit_or_send(callback.message, texts.choose_monthly_year(), reply_markup=keyboard)
        return
    await callback.message.answer(texts.invalid_choice())


@router.callback_query(F.data == "back:mode")
async def handle_back_mode(callback: CallbackQuery):
    await callback.answer()
    settings = get_settings(callback.bot)
    year_years = media.available_yearly_years(settings.media_dir)
    month_years = media.available_monthly_years(settings.media_dir)
    keyboard = build_layout_keyboard(has_year=bool(year_years), has_month=bool(month_years))
    await _edit_or_send(callback.message, texts.welcome(), reply_markup=keyboard)


@router.callback_query(F.data.startswith("m-year:"))
async def handle_month_year(callback: CallbackQuery):
    year = parse_month_year_data(callback.data or "")
    await callback.answer()
    if not year:
        await callback.message.answer(texts.invalid_year())
        return
    settings = get_settings(callback.bot)
    years = media.available_monthly_years(settings.media_dir)
    if year not in years:
        await callback.message.answer(texts.year_unavailable())
        return
    months = media.months_for_year(settings.media_dir, year)
    if not months:
        await callback.message.answer(texts.months_missing())
        return
    keyboard = build_months_keyboard(settings.media_dir, year, back="back:m-years")
    await _edit_or_send(callback.message, texts.year_prompt(year), reply_markup=keyboard)


@router.callback_query(F.data == "back:m-years")
async def handle_back_month_years(callback: CallbackQuery):
    await callback.answer()
    settings = get_settings(callback.bot)
    month_years = media.available_monthly_years(settings.media_dir)
    if not month_years:
        await callback.message.answer(texts.month_section_empty())
        return
    keyboard = build_years_keyboard(month_years, prefix="m-year", back="back:mode")
    await _edit_or_send(callback.message, texts.choose_monthly_year(), reply_markup=keyboard)


@router.callback_query(F.data.startswith("m-month:"))
async def handle_month(callback: CallbackQuery):
    ym = parse_month_data(callback.data or "")
    await callback.answer()
    if not ym:
        await callback.message.answer(texts.invalid_month())
        return
    year = ym.split("-")[0]
    settings = get_settings(callback.bot)
    media_dir = settings.media_dir
    if year not in media.available_monthly_years(media_dir):
        await callback.message.answer(texts.year_unavailable())
        return
    if ym not in media.months_for_year(media_dir, year):
        await callback.message.answer(texts.month_unavailable())
        return
    signs = media.available_month_signs(media_dir, ym)
    if not signs:
        await callback.message.answer(texts.month_content_missing())
        return
    keyboard = build_month_signs_keyboard(media_dir, ym, back=f"back:m-months:{year}")
    month_name = media.month_name_from_ym(ym) or "Месяц"
    await _edit_or_send(callback.message, texts.month_prompt(month_name, year), reply_markup=keyboard)


@router.callback_query(F.data.startswith("back:m-months:"))
async def handle_back_months(callback: CallbackQuery):
    await callback.answer()
    year = (callback.data or "").split(":", maxsplit=2)[-1]
    settings = get_settings(callback.bot)
    if year not in media.available_monthly_years(settings.media_dir):
        await callback.message.answer(texts.year_unavailable())
        return
    months = media.months_for_year(settings.media_dir, year)
    if not months:
        await callback.message.answer(texts.months_missing())
        return
    keyboard = build_months_keyboard(settings.media_dir, year, back="back:m-years")
    await _edit_or_send(callback.message, texts.year_prompt(year), reply_markup=keyboard)


@router.callback_query(F.data.startswith("m-sign:"))
async def handle_month_sign(callback: CallbackQuery):
    parsed = parse_month_sign_data(callback.data or "")
    await callback.answer()
    if not parsed:
        await callback.message.answer(texts.invalid_sign())
        return
    ym, sign = parsed
    year = ym.split("-")[0]
    settings = get_settings(callback.bot)
    media_dir = settings.media_dir
    if year not in media.available_monthly_years(media_dir):
        await callback.message.answer(texts.year_unavailable())
        return
    if ym not in media.months_for_year(media_dir, year):
        await callback.message.answer(texts.month_unavailable())
        return
    if sign not in media.available_month_signs(media_dir, ym):
        await callback.message.answer(texts.sign_unavailable())
        return
    content_path = media.find_month_content_path(media_dir, ym, sign)
    if not content_path:
        await callback.message.answer(texts.content_missing())
        return
    product_id = media.build_month_product_id(ym, sign)
    if not product_id:
        await callback.message.answer(texts.invalid_product())
        return
    month_name = media.month_name_from_ym(ym) or ym
    price_rub = settings.price_kopeks / 100
    text = texts.price_caption_month(month_name, ym.split("-")[0], sign, price_rub)
    back_cb = f"back:m-signs:{ym}"
    await _edit_or_send(callback.message, text, reply_markup=build_pay_keyboard(product_id, back=back_cb))


@router.callback_query(F.data.startswith("back:m-signs:"))
async def handle_back_month_signs(callback: CallbackQuery):
    await callback.answer()
    ym = (callback.data or "").split(":", maxsplit=2)[-1]
    year = ym.split("-")[0] if "-" in ym else None
    if not year:
        await callback.message.answer(texts.invalid_month())
        return
    settings = get_settings(callback.bot)
    media_dir = settings.media_dir
    if year not in media.available_monthly_years(media_dir):
        await callback.message.answer(texts.year_unavailable())
        return
    if ym not in media.months_for_year(media_dir, year):
        await callback.message.answer(texts.month_unavailable())
        return
    signs = media.available_month_signs(media_dir, ym)
    if not signs:
        await callback.message.answer(texts.month_content_missing())
        return
    keyboard = build_month_signs_keyboard(media_dir, ym, back=f"back:m-months:{year}")
    month_name = media.month_name_from_ym(ym) or "Месяц"
    await _edit_or_send(callback.message, texts.month_prompt(month_name, year), reply_markup=keyboard)


@router.callback_query(F.data.startswith("y-year:"))
async def handle_year(callback: CallbackQuery):
    year = parse_year_data(callback.data or "")
    await callback.answer()
    if not year:
        await callback.message.answer(texts.invalid_year())
        return
    settings = get_settings(callback.bot)
    media_dir = settings.media_dir
    if year not in media.available_yearly_years(media_dir):
        await callback.message.answer(texts.year_unavailable())
        return
    signs = media.available_year_signs(media_dir, year)
    if not signs:
        await callback.message.answer(texts.year_content_missing())
        return
    keyboard = build_year_signs_keyboard(media_dir, year, back="back:y-years")
    await _edit_or_send(callback.message, texts.year_sign_prompt(year), reply_markup=keyboard)


@router.callback_query(F.data == "back:y-years")
async def handle_back_year_years(callback: CallbackQuery):
    await callback.answer()
    settings = get_settings(callback.bot)
    year_years = media.available_yearly_years(settings.media_dir)
    if not year_years:
        await callback.message.answer(texts.year_section_empty())
        return
    keyboard = build_years_keyboard(year_years, prefix="y-year", back="back:mode")
    await _edit_or_send(callback.message, texts.choose_yearly_year(), reply_markup=keyboard)


@router.callback_query(F.data.startswith("y-sign:"))
async def handle_year_sign(callback: CallbackQuery):
    parsed = parse_year_sign_data(callback.data or "")
    await callback.answer()
    if not parsed:
        await callback.message.answer(texts.invalid_sign())
        return
    year, sign = parsed
    settings = get_settings(callback.bot)
    media_dir = settings.media_dir
    if year not in media.available_yearly_years(media_dir):
        await callback.message.answer(texts.year_unavailable())
        return
    if sign not in media.available_year_signs(media_dir, year):
        await callback.message.answer(texts.sign_unavailable())
        return
    content_path = media.find_year_content_path(media_dir, year, sign)
    if not content_path:
        await callback.message.answer(texts.content_missing())
        return
    product_id = media.build_year_product_id(year, sign)
    if not product_id:
        await callback.message.answer(texts.invalid_product())
        return
    price_rub = settings.price_kopeks / 100
    text = texts.price_caption_year(year, sign, price_rub)
    back_cb = f"back:y-signs:{year}"
    await _edit_or_send(callback.message, text, reply_markup=build_pay_keyboard(product_id, back=back_cb))


@router.callback_query(F.data.startswith("back:y-signs:"))
async def handle_back_year_signs(callback: CallbackQuery):
    await callback.answer()
    year = (callback.data or "").split(":", maxsplit=2)[-1]
    settings = get_settings(callback.bot)
    media_dir = settings.media_dir
    if year not in media.available_yearly_years(media_dir):
        await callback.message.answer(texts.year_unavailable())
        return
    signs = media.available_year_signs(media_dir, year)
    if not signs:
        await callback.message.answer(texts.year_content_missing())
        return
    keyboard = build_year_signs_keyboard(media_dir, year, back="back:y-years")
    await _edit_or_send(callback.message, texts.year_sign_prompt(year), reply_markup=keyboard)


async def send_invoice(callback: CallbackQuery, product_id: str) -> None:
    settings = get_settings(callback.bot)
    parsed = parse_product(product_id)
    if not parsed:
        await callback.message.answer(texts.invalid_product())
        return
    sign_name = SIGNS_RU.get(parsed["sign"], parsed["sign"])
    if parsed["kind"] == "month" and parsed["month"]:
        ym = f"{parsed['year']}-{parsed['month']}"
        month_name = media.month_name_from_ym(ym) or ym
        title = f"{month_name} {parsed['year']}"
        description = f"Гороскоп {month_name.lower()} для знака {sign_name}"
    else:
        title = f"{parsed['year']} год"
        description = f"Годовой гороскоп для знака {sign_name}"
    prices = [LabeledPrice(label="Гороскоп", amount=settings.price_kopeks)]
    payload = f"{product_id}|{callback.from_user.id}"
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
    await send_invoice(callback, product_id)


@router.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery):
    parsed = parse_invoice_payload(query.invoice_payload)
    if not parsed:
        await query.answer(ok=False, error_message="Заказ недоступен.")
        logger.info("Pre-checkout rejected user=%s payload=%s", query.from_user.id, query.invoice_payload)
        return
    product, user_id = parsed
    if user_id != query.from_user.id:
        await query.answer(ok=False, error_message="Заказ недоступен.")
        logger.info("Pre-checkout rejected user mismatch=%s payload=%s", query.from_user.id, query.invoice_payload)
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


async def deliver_file(bot: Bot, chat_id: int, order: Order, content_path: Path) -> bool:
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
        await db.mark_delivered(get_db_path(bot), order["id"])
        logger.info("Content sent user=%s order_id=%s", chat_id, order["id"])
    return delivered


async def prompt_review(bot: Bot, chat_id: int, order: Order) -> None:
    await bot.send_message(chat_id, texts.review_prompt(), reply_markup=build_review_keyboard(order["id"]))


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    settings = get_settings(message.bot)
    parsed_payload = parse_invoice_payload(payload)
    if not parsed_payload:
        await message.answer(texts.invalid_product())
        return
    product, user_id = parsed_payload
    if user_id != message.from_user.id:
        await message.answer(texts.order_not_found())
        return
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
    if not product_id:
        await message.answer(texts.invalid_product())
        return
    order = await db.create_paid_order(
        settings.db_path,
        message.from_user.id,
        product_id,
        settings.price_kopeks,
        settings.currency,
        payment.telegram_payment_charge_id,
    )
    logger.info(
        "Payment successful user=%s order_id=%s payload=%s charge_id=%s",
        message.from_user.id,
        order["id"],
        payload,
        payment.telegram_payment_charge_id,
    )
    await message.answer(texts.payment_success())
    delivered = await deliver_file(message.bot, message.chat.id, order, content_path)
    if delivered:
        await prompt_review(message.bot, message.chat.id, order)


@router.callback_query(F.data.startswith("review:start:"))
async def handle_review_start(callback: CallbackQuery):
    order_id = (callback.data or "").split(":", maxsplit=2)[-1]
    await callback.answer()
    order = await db.get_order(get_db_path(callback.bot), order_id)
    if not order or order["user_id"] != callback.from_user.id:
        await callback.message.answer(texts.review_expired())
        return
    review = await db.create_review_request(get_db_path(callback.bot), order_id, order["user_id"], order["product_id"])
    if review["status"] != "pending":
        await callback.message.answer(texts.review_expired())
        return
    try:
        await callback.message.edit_reply_markup()
    except Exception:
        pass
    await callback.message.answer(texts.review_request(), reply_markup=ForceReply(selective=True))


@router.callback_query(F.data.startswith("review:skip:"))
async def handle_review_skip(callback: CallbackQuery):
    order_id = (callback.data or "").split(":", maxsplit=2)[-1]
    await callback.answer()
    order = await db.get_order(get_db_path(callback.bot), order_id)
    if not order or order["user_id"] != callback.from_user.id:
        await callback.message.answer(texts.review_expired())
        return
    review = await db.create_review_request(get_db_path(callback.bot), order_id, order["user_id"], order["product_id"])
    if review["status"] == "submitted":
        await callback.message.answer(texts.review_expired())
        return
    await db.mark_review_declined(get_db_path(callback.bot), order_id, order["user_id"], order["product_id"])
    try:
        await callback.message.edit_reply_markup()
    except Exception:
        pass


@router.message(F.text)
async def handle_review_text(message: Message):
    if not message.text or message.text.startswith("/"):
        return
    review_text = message.text.strip()
    if not review_text:
        return
    if len(review_text) < 100:
        await message.answer(texts.review_request())
        return
    pending = await db.get_pending_review_for_user(get_db_path(message.bot), message.from_user.id)
    if not pending:
        return
    await db.mark_review_submitted(get_db_path(message.bot), pending["order_id"], review_text)
    parsed = parse_product(pending["product_id"])
    if parsed:
        reward_path = media.find_review_image(get_settings(message.bot).media_dir, parsed["sign"])
        if reward_path:
            caption = texts.review_reward_caption(parsed["sign"])
            await send_content(message.bot, message.chat.id, reward_path, caption)
    await message.answer(texts.review_thanks())

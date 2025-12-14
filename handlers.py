import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    Optional,
    PreCheckoutQuery,
)

import catalog
import db
from config import Settings
from const import MONTH_NAMES_RU, SIGNS_RU
from utils import (
    build_months_keyboard,
    build_pay_keyboard,
    build_signs_keyboard,
    build_years_keyboard,
    parse_month_data,
    parse_pay_data,
    parse_product,
    parse_sign_data,
    parse_year_data,
    send_content,
)

logger = logging.getLogger(__name__)

router = Router()

_settings: Settings | None = None


def setup(settings: Settings) -> None:
    """Configure handlers with shared settings instance."""
    global _settings
    _settings = settings


def get_settings(bot: Bot):
    if _settings is None:
        raise RuntimeError("Handlers are not configured with settings")
    return _settings


def get_db_path(bot: Bot) -> Path:
    return get_settings(bot).db_path


@router.message(Command("start"))
async def handle_start(message: Message):
    settings = get_settings(message.bot)
    years = catalog.available_years(settings.media_dir)
    if not years:
        await message.answer("Контент пока не готов. Загляни позже.")
        return
    keyboard = build_years_keyboard(years)
    await message.answer("Выбери год:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("year:"))
async def handle_year(callback: CallbackQuery):
    year = parse_year_data(callback.data or "")
    await callback.answer()
    if not year:
        await callback.message.answer("Некорректный год.")
        return
    settings = get_settings(callback.bot)
    years = catalog.available_years(settings.media_dir)
    if year not in years:
        await callback.message.answer("Этот год недоступен.")
        return
    months = catalog.months_for_year(settings.media_dir, year)
    if not months:
        await callback.message.answer("Месяцы для этого года не найдены.")
        return
    keyboard = build_months_keyboard(settings.media_dir, year)
    await callback.message.answer(f"Год {year}. Выбери месяц:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("month:"))
async def handle_month(callback: CallbackQuery):
    ym = parse_month_data(callback.data or "")
    await callback.answer()
    if not ym:
        await callback.message.answer("Некорректный месяц.")
        return
    year = ym.split("-")[0]
    settings = get_settings(callback.bot)
    media_dir = settings.media_dir
    if year not in catalog.available_years(media_dir):
        await callback.message.answer("Этот год недоступен.")
        return
    if ym not in catalog.months_for_year(media_dir, year):
        await callback.message.answer("Этот месяц недоступен.")
        return
    signs = catalog.available_signs(media_dir, ym)
    if not signs:
        await callback.message.answer("Контент для этого месяца пока не готов.")
        return
    keyboard = build_signs_keyboard(media_dir, ym)
    month_name = catalog.month_name_from_ym(ym) or "Месяц"
    await callback.message.answer(
        f"{month_name} {year}. Выбери знак:", reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("sign:"))
async def handle_sign(callback: CallbackQuery):
    parsed = parse_sign_data(callback.data or "")
    await callback.answer()
    if not parsed:
        await callback.message.answer("Некорректный выбор.")
        return
    ym, sign = parsed
    year = ym.split("-")[0]
    settings = get_settings(callback.bot)
    media_dir = settings.media_dir
    if year not in catalog.available_years(media_dir):
        await callback.message.answer("Этот год недоступен.")
        return
    if ym not in catalog.months_for_year(media_dir, year):
        await callback.message.answer("Этот месяц недоступен.")
        return
    if sign not in catalog.available_signs(media_dir, ym):
        await callback.message.answer("Этот знак недоступен.")
        return
    content_path = catalog.find_content_path(media_dir, ym, sign)
    if not content_path:
        await callback.message.answer("Контент для выбранного месяца пока не готов.")
        return
    product_id = catalog.build_product_id(ym, sign)
    if not product_id:
        await callback.message.answer("Некорректный товар.")
        return
    order = await db.create_order(
        settings.db_path,
        callback.from_user.id,
        product_id,
        settings.price_kopeks,
        settings.currency,
    )
    logger.info("Order created user=%s order_id=%s", callback.from_user.id, order["id"])
    month_name = catalog.month_name_from_ym(ym) or ym
    sign_name = SIGNS_RU.get(sign, sign)
    price_rub = settings.price_kopeks / 100
    text = f"{month_name} {ym.split('-')[0]}, {sign_name}. Цена {price_rub:.0f} ₽"
    await callback.message.answer(text, reply_markup=build_pay_keyboard(order["id"]))


def parse_product(product_id: str) -> Optional[tuple[str, str]]:
    parts = product_id.split(":")
    if len(parts) != 2:
        return None
    ym, sign = parts
    if not catalog.parse_year_month(ym) or sign not in SIGNS_RU:
        return None
    return ym, sign


async def send_invoice(callback: CallbackQuery, order: dict) -> None:
    settings = get_settings(callback.bot)
    parsed = parse_product(order["product_id"])
    if not parsed:
        await callback.message.answer("Некорректный товар.")
        return
    ym, sign = parsed
    month_name = catalog.month_name_from_ym(ym) or ym
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
        await callback.message.answer("Некорректный заказ.")
        return
    settings = get_settings(callback.bot)
    order = await db.get_order(settings.db_path, order_id)
    if not order or order["user_id"] != callback.from_user.id:
        await callback.message.answer("Заказ не найден.")
        return
    parsed = parse_product(order["product_id"])
    if not parsed:
        await callback.message.answer("Некорректный товар.")
        return
    ym, sign = parsed
    media_dir = settings.media_dir
    if ym not in catalog.months_for_year(
        media_dir, ym.split("-")[0]
    ) or sign not in catalog.available_signs(media_dir, ym):
        await callback.message.answer("Контент для выбранного месяца пока не готов.")
        return
    content_path = catalog.find_content_path(media_dir, ym, sign)
    if not content_path:
        await callback.message.answer("Контент для выбранного месяца пока не готов.")
        return
    if order["status"] == "paid":
        await callback.message.answer("Заказ уже оплачен, отправляю файл.")
        await deliver_file(callback.bot, callback.message.chat.id, order, content_path)
        return
    await send_invoice(callback, order)


@router.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery):
    settings = get_settings(query.bot)
    order = await db.get_order(settings.db_path, query.invoice_payload)
    if not order or order["user_id"] != query.from_user.id or order["status"] == "paid":
        await query.answer(ok=False, error_message="Заказ недоступен.")
        logger.info(
            "Pre-checkout rejected user=%s order_id=%s",
            query.from_user.id,
            query.invoice_payload,
        )
        return
    await query.answer(ok=True)
    logger.info("Pre-checkout ok user=%s order_id=%s", query.from_user.id, order["id"])


async def deliver_file(bot: Bot, chat_id: int, order: dict, content_path: Path) -> None:
    parsed = parse_product(order["product_id"])
    if not parsed:
        await bot.send_message(chat_id, "Не удалось отправить файл.")
        return
    ym, sign = parsed
    month_name = catalog.month_name_from_ym(ym) or ym
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
        await message.answer("Заказ не найден.")
        return
    try:
        await db.mark_paid(
            settings.db_path, order_id, payment.telegram_payment_charge_id
        )
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
        await message.answer("Не удалось определить товар.")
        return
    ym, sign = parsed
    content_path = catalog.find_content_path(settings.media_dir, ym, sign)
    if not content_path:
        await message.answer("Файл не найден. Напиши нам, мы вернем оплату.")
        return
    await deliver_file(message.bot, message.chat.id, order, content_path)

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app import texts
from app.features.user.dependencies import get_settings
from app.features.user.keyboards import (
    build_layout_keyboard,
    build_month_signs_keyboard,
    build_months_keyboard,
    build_pay_keyboard,
    build_year_signs_keyboard,
    build_years_keyboard,
)
from app.services import media
from app.services.pricing import get_price_kopeks
from app.services.parsing import (
    parse_layout_choice,
    parse_month_data,
    parse_month_sign_data,
    parse_month_year_data,
    parse_year_data,
    parse_year_sign_data,
)

logger = logging.getLogger(__name__)

router = Router()


async def _edit_or_send(message: Message, text: str, reply_markup):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        await message.answer(text, reply_markup=reply_markup)


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
    price_rub = get_price_kopeks("month", pricing_path=settings.pricing_path) / 100
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
    price_rub = get_price_kopeks("year", pricing_path=settings.pricing_path) / 100
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

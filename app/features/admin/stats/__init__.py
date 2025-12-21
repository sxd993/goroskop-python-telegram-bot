from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.config import MONTH_NAMES_RU, SIGNS_RU
from app import texts
from app.features.admin.dependencies import get_settings, is_admin
from app.features.admin.keyboards import (
    ADMIN_STATS_CALLBACK,
    ADMIN_STATS_MONTH_OPEN_PREFIX,
    ADMIN_STATS_MONTHS_PAGE_PREFIX,
    build_admin_menu,
    build_admin_stats_month_detail_keyboard,
    build_admin_stats_months_keyboard,
)
from app.features.admin.keyboards import SIGN_EMOJI
from app.features.admin.utils import edit_or_send
from app.services import db, media

router = Router()

MONTHS_PAGE_SIZE = 8


async def _show_months_page(callback: CallbackQuery, *, page: int) -> None:
    if page < 1:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return

    settings = get_settings(callback.bot)
    offset = (page - 1) * MONTHS_PAGE_SIZE
    raw = await db.fetch_paid_months_page(settings.db_path, limit=MONTHS_PAGE_SIZE + 1, offset=offset)
    if not raw:
        await callback.answer(texts.admin_stats_empty() if page == 1 else texts.invalid_choice(), show_alert=page != 1)
        if page == 1:
            await edit_or_send(callback, texts.admin_stats_empty(), reply_markup=build_admin_menu())
        return

    has_next = len(raw) > MONTHS_PAGE_SIZE
    months = raw[:MONTHS_PAGE_SIZE]

    items: list[tuple[str, str]] = []
    for ym in months:
        month_name = media.month_name_from_ym(ym) or ym
        year = ym.split("-")[0] if "-" in ym else ym
        items.append((f"🗓️ {month_name} {year}", ym))

    markup = build_admin_stats_months_keyboard(items, page=page, has_prev=page > 1, has_next=has_next)
    await callback.answer()
    await edit_or_send(callback, texts.admin_stats_choose_month(page), reply_markup=markup)


@router.callback_query(F.data == ADMIN_STATS_CALLBACK)
async def handle_admin_stats(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    await _show_months_page(callback, page=1)


@router.callback_query(F.data.startswith(f"{ADMIN_STATS_MONTHS_PAGE_PREFIX}:"))
async def handle_admin_stats_months_page(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    raw_page = (callback.data or "").split(":")[-1]
    try:
        page = int(raw_page)
    except ValueError:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return
    await _show_months_page(callback, page=page)


@router.callback_query(F.data.startswith(f"{ADMIN_STATS_MONTH_OPEN_PREFIX}:"))
async def handle_admin_stats_month_open(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()

    parts = (callback.data or "").split(":")
    if len(parts) < 4:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return
    ym = parts[-2]
    raw_page = parts[-1]
    try:
        page = int(raw_page)
    except ValueError:
        page = 1

    match = media.parse_year_month(ym)
    if not match:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return

    year = match.group("year")
    month = int(match.group("month"))
    month_name = MONTH_NAMES_RU.get(month, f"{month:02d}")

    settings = get_settings(callback.bot)
    rows = await db.fetch_month_sales_breakdown(settings.db_path, ym=ym)
    if not rows:
        await callback.answer()
        await edit_or_send(
            callback,
            texts.admin_stats_month_empty(month_name, year),
            reply_markup=build_admin_stats_month_detail_keyboard(page=page),
        )
        return

    total_count = 0
    total_amount = 0
    lines = [texts.admin_stats_month_title(month_name, year)]
    for sign, count, total in rows:
        sign_name = SIGNS_RU.get(sign, sign)
        emoji = SIGN_EMOJI.get(sign, "🔮")
        lines.append(f"{emoji} {sign_name}: {count} шт. / {total/100:.0f} ₽")
        total_count += int(count)
        total_amount += int(total)
    lines.append("")
    lines.append(texts.admin_stats_total(total_count, total_amount / 100))

    await callback.answer()
    await edit_or_send(
        callback,
        "\n".join(lines),
        reply_markup=build_admin_stats_month_detail_keyboard(page=page),
    )

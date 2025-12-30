from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app import texts
from app.config import MONTH_NAMES_RU
from app.features.admin.dependencies import get_settings, is_admin
from app.features.admin.keyboards import (
    ADMIN_REVIEWS_CALLBACK,
    ADMIN_REVIEWS_FILTER_PAGE_PREFIX,
    ADMIN_REVIEWS_KIND_PREFIX,
    ADMIN_REVIEWS_MONTHS_PAGE_PREFIX,
    ADMIN_REVIEWS_MONTH_OPEN_PREFIX,
    ADMIN_REVIEWS_PAGE_PREFIX,
    ADMIN_REVIEW_OPEN_PREFIX,
    build_admin_menu,
    build_admin_review_detail_keyboard,
    build_admin_reviews_kind_keyboard,
    build_admin_reviews_list_keyboard,
    build_admin_reviews_months_keyboard,
)
from app.features.admin.utils import REVIEWS_PAGE_SIZE, edit_or_send, format_dt, product_label
from app.services import db

router = Router()

REVIEWS_MONTHS_PAGE_SIZE = 9


def _month_label(ym: str) -> str:
    parts = ym.split("-")
    if len(parts) != 2:
        return ym
    year, month = parts
    try:
        month_idx = int(month)
    except ValueError:
        return ym
    name = MONTH_NAMES_RU.get(month_idx, month)
    return f"{name} {year}"


def _build_reviews_page_cb(page: int, kind: str, ym: str | None, month_page: int) -> str:
    ym_value = ym or "-"
    return f"{ADMIN_REVIEWS_FILTER_PAGE_PREFIX}:{page}:{kind}:{ym_value}:{month_page}"


def _compact_ym(ym: str | None) -> str:
    if not ym:
        return "-"
    return ym.replace("-", "")


def _expand_ym(value: str) -> str | None:
    if not value or value == "-":
        return None
    if len(value) == 6 and value.isdigit():
        return f"{value[:4]}-{value[4:]}"
    return value


def _build_review_open_cb(review_id: str, page: int, kind: str, ym: str | None, month_page: int) -> str:
    kind_code = "m" if kind == "month" else "y"
    return f"{ADMIN_REVIEW_OPEN_PREFIX}:{review_id}:{page}:{kind_code}:{_compact_ym(ym)}:{month_page}"


async def _show_reviews_type_menu(callback: CallbackQuery) -> None:
    await edit_or_send(
        callback,
        texts.admin_reviews_kind_prompt(),
        reply_markup=build_admin_reviews_kind_keyboard(),
    )


async def _show_reviews_list(
    callback: CallbackQuery,
    *,
    kind: str,
    ym: str | None,
    page: int,
    month_page: int,
    title: str,
) -> None:
    if page < 1:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return

    settings = get_settings(callback.bot)
    offset = (page - 1) * REVIEWS_PAGE_SIZE
    raw = await db.fetch_reviews_page_filtered(
        settings.db_path,
        kind=kind,
        ym=ym,
        limit=REVIEWS_PAGE_SIZE + 1,
        offset=offset,
    )
    if not raw:
        await callback.answer(texts.admin_reviews_empty() if page == 1 else texts.invalid_choice(), show_alert=page != 1)
        if page == 1:
            await edit_or_send(callback, texts.admin_reviews_empty(), reply_markup=build_admin_menu())
        return

    has_next = len(raw) > REVIEWS_PAGE_SIZE
    reviews = raw[:REVIEWS_PAGE_SIZE]
    items: list[tuple[str, str]] = []
    for idx, review in enumerate(reviews, start=1):
        status = review["status"]
        icon = "✅" if status == "submitted" else "🚫"
        created = format_dt(review["created_at"])
        order_tag = review["order_id"][:8]
        review_title = product_label(review["product_id"])
        button_text = f"{idx}. {icon} {created} | {order_tag} | {review_title}"
        if len(button_text) > 64:
            button_text = f"{button_text[:61]}…"
        items.append((button_text, _build_review_open_cb(review["id"], page, kind, ym, month_page)))

    prev_cb = _build_reviews_page_cb(page - 1, kind, ym, month_page) if page > 1 else None
    next_cb = _build_reviews_page_cb(page + 1, kind, ym, month_page) if has_next else None
    back_menu_cb = ADMIN_REVIEWS_CALLBACK if kind == "year" else f"{ADMIN_REVIEWS_MONTHS_PAGE_PREFIX}:{month_page}"
    markup = build_admin_reviews_list_keyboard(
        items,
        prev_callback=prev_cb,
        next_callback=next_cb,
        back_callback=back_menu_cb,
    )
    await callback.answer()
    await edit_or_send(callback, texts.admin_reviews_filtered_title(title, page), reply_markup=markup)


async def _show_reviews_months_page(callback: CallbackQuery, *, page: int) -> None:
    if page < 1:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return
    settings = get_settings(callback.bot)
    offset = (page - 1) * REVIEWS_MONTHS_PAGE_SIZE
    raw = await db.fetch_review_months_page(settings.db_path, limit=REVIEWS_MONTHS_PAGE_SIZE + 1, offset=offset)
    if not raw:
        await callback.answer(texts.admin_reviews_months_empty() if page == 1 else texts.invalid_choice(), show_alert=page != 1)
        if page == 1:
            await edit_or_send(callback, texts.admin_reviews_months_empty(), reply_markup=build_admin_menu())
        return
    has_next = len(raw) > REVIEWS_MONTHS_PAGE_SIZE
    months = raw[:REVIEWS_MONTHS_PAGE_SIZE]
    items = [(_month_label(ym), ym) for ym in months]
    prev_cb = f"{ADMIN_REVIEWS_MONTHS_PAGE_PREFIX}:{page - 1}" if page > 1 else None
    next_cb = f"{ADMIN_REVIEWS_MONTHS_PAGE_PREFIX}:{page + 1}" if has_next else None
    markup = build_admin_reviews_months_keyboard(
        items,
        page=page,
        prev_callback=prev_cb,
        next_callback=next_cb,
    )
    await callback.answer()
    await edit_or_send(callback, texts.admin_reviews_months_title(page), reply_markup=markup)


@router.callback_query(F.data == ADMIN_REVIEWS_CALLBACK)
async def handle_admin_reviews(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    await _show_reviews_type_menu(callback)


@router.callback_query(F.data.startswith(f"{ADMIN_REVIEWS_PAGE_PREFIX}:"))
async def handle_admin_reviews_page_legacy(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    await _show_reviews_type_menu(callback)


@router.callback_query(F.data.startswith(f"{ADMIN_REVIEWS_KIND_PREFIX}:"))
async def handle_admin_reviews_kind(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    kind = (callback.data or "").split(":")[-1]
    if kind == "year":
        await _show_reviews_list(callback, kind="year", ym=None, page=1, month_page=1, title="Годовые отзывы")
        return
    if kind == "month":
        await _show_reviews_months_page(callback, page=1)
        return
    await callback.answer(texts.invalid_choice(), show_alert=True)


@router.callback_query(F.data.startswith(f"{ADMIN_REVIEWS_MONTHS_PAGE_PREFIX}:"))
async def handle_admin_reviews_months_page(callback: CallbackQuery, state: FSMContext):
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
    await _show_reviews_months_page(callback, page=page)


@router.callback_query(F.data.startswith(f"{ADMIN_REVIEWS_MONTH_OPEN_PREFIX}:"))
async def handle_admin_reviews_month_open(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    parts = (callback.data or "").split(":")
    if len(parts) < 3:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return
    ym = parts[2]
    month_page = 1
    if len(parts) > 3:
        try:
            month_page = int(parts[3])
        except ValueError:
            month_page = 1
    title = f"Отзывы за {_month_label(ym)}"
    await _show_reviews_list(callback, kind="month", ym=ym, page=1, month_page=month_page, title=title)


@router.callback_query(F.data.startswith(f"{ADMIN_REVIEWS_FILTER_PAGE_PREFIX}:"))
async def handle_admin_reviews_filtered_page(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    parts = (callback.data or "").split(":")
    if len(parts) < 6:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return
    try:
        page = int(parts[2])
    except ValueError:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return
    kind = parts[3]
    ym_value = parts[4]
    ym = None if ym_value == "-" else ym_value
    try:
        month_page = int(parts[5])
    except ValueError:
        month_page = 1
    title = "Годовые отзывы" if kind == "year" else f"Отзывы за {_month_label(ym or '')}"
    await _show_reviews_list(callback, kind=kind, ym=ym, page=page, month_page=month_page, title=title)


@router.callback_query(F.data.startswith(f"{ADMIN_REVIEW_OPEN_PREFIX}:"))
async def handle_admin_review_open(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    parts = (callback.data or "").split(":")
    if len(parts) < 2:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return
    review_id = ""
    back_callback = ADMIN_REVIEWS_CALLBACK
    if len(parts) >= 7 and parts[0] == "ar" and parts[1] == "o":
        review_id = parts[2]
        try:
            page = int(parts[3])
        except ValueError:
            page = 1
        kind = "month" if parts[4] == "m" else "year"
        ym = _expand_ym(parts[5])
        try:
            month_page = int(parts[6])
        except ValueError:
            month_page = 1
        back_callback = _build_reviews_page_cb(page, kind, ym, month_page)
    else:
        legacy_id = ""
        if len(parts) >= 3 and "-" in parts[2]:
            legacy_id = parts[2]
        elif "-" in parts[1]:
            legacy_id = parts[1]
        elif len(parts) >= 4 and "-" in parts[-2]:
            legacy_id = parts[-2]
        if legacy_id:
            review_id = legacy_id
            back_callback = ADMIN_REVIEWS_CALLBACK
    if not review_id:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return

    settings = get_settings(callback.bot)
    review = await db.get_review(settings.db_path, review_id)
    if not review:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return

    created = format_dt(review["created_at"])
    order_tag = review["order_id"][:8]
    title = product_label(review["product_id"])
    text = review.get("text") or "—"
    await callback.answer()
    await edit_or_send(
        callback,
        texts.admin_review_detail(
            title=title,
            created=created,
            order_tag=order_tag,
            user_id=review["user_id"],
            status=review["status"],
            text=text,
            contact_phone=review.get("contact_phone"),
            contact_username=review.get("contact_username"),
        ),
        reply_markup=build_admin_review_detail_keyboard(back_callback=back_callback),
    )

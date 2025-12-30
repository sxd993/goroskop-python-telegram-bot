from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app import texts
from app.features.admin.dependencies import get_settings, is_admin
from app.features.admin.keyboards import (
    ADMIN_REVIEWS_CALLBACK,
    ADMIN_REVIEWS_PAGE_PREFIX,
    ADMIN_REVIEW_OPEN_PREFIX,
    build_admin_review_detail_keyboard,
    build_admin_reviews_list_keyboard,
    build_admin_menu,
)
from app.features.admin.utils import REVIEWS_PAGE_SIZE, edit_or_send, format_dt, product_label
from app.services import db

router = Router()


async def _show_reviews_page(callback: CallbackQuery, *, page: int) -> None:
    if page < 1:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return

    settings = get_settings(callback.bot)
    offset = (page - 1) * REVIEWS_PAGE_SIZE
    raw = await db.fetch_reviews_page(settings.db_path, limit=REVIEWS_PAGE_SIZE + 1, offset=offset)
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
        title = product_label(review["product_id"])
        button_text = f"{idx}. {icon} {created} | {order_tag} | {title}"
        if len(button_text) > 64:
            button_text = f"{button_text[:61]}…"
        items.append((button_text, review["id"]))

    markup = build_admin_reviews_list_keyboard(
        items,
        page=page,
        has_prev=page > 1,
        has_next=has_next,
    )
    await callback.answer()
    await edit_or_send(callback, texts.admin_reviews_page_title(page), reply_markup=markup)


@router.callback_query(F.data == ADMIN_REVIEWS_CALLBACK)
async def handle_admin_reviews(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    await _show_reviews_page(callback, page=1)


@router.callback_query(F.data.startswith(f"{ADMIN_REVIEWS_PAGE_PREFIX}:"))
async def handle_admin_reviews_page(callback: CallbackQuery, state: FSMContext):
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
    await _show_reviews_page(callback, page=page)


@router.callback_query(F.data.startswith(f"{ADMIN_REVIEW_OPEN_PREFIX}:"))
async def handle_admin_review_open(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    parts = (callback.data or "").split(":")
    if len(parts) < 4:
        await callback.answer(texts.invalid_choice(), show_alert=True)
        return
    review_id = parts[-2]
    raw_page = parts[-1]
    try:
        page = int(raw_page)
    except ValueError:
        page = 1

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
        reply_markup=build_admin_review_detail_keyboard(page=page),
    )

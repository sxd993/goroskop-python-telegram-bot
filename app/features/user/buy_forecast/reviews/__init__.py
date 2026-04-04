import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app import texts
from app.features.user.dependencies import get_db_path, get_settings
from app.features.user.keyboards import (
    REVIEW_CANCEL_CALLBACK,
    REVIEW_MENU_CALLBACK,
    build_review_cancel_keyboard,
    build_review_contact_keyboard,
    build_review_keyboard,
    remove_keyboard,
)
from app.services import db, media, state_machine
from app.services.messaging import send_content, send_message_safe
from app.services.parsing import parse_product
from app.services.state_machine import InvalidStateTransition, UserState

logger = logging.getLogger(__name__)

router = Router()


async def prompt_review(bot, chat_id: int, order: dict) -> None:  # type: ignore[name-defined]
    await send_message_safe(bot, chat_id, texts.review_prompt(), reply_markup=build_review_keyboard(order["id"]))


@router.callback_query(F.data.startswith("review:start:"))
async def handle_review_start(callback: CallbackQuery):
    order_id = (callback.data or "").split(":", maxsplit=2)[-1]
    await callback.answer()
    db_path = get_db_path(callback.bot)
    user_state = await state_machine.get_user_state(db_path, callback.from_user.id)
    if user_state != UserState.REVIEW_PENDING:
        await callback.message.answer(texts.review_expired())
        return
    user = await db.get_user(db_path, callback.from_user.id)
    if user and user.get("last_order_id") and user["last_order_id"] != order_id:
        await callback.message.answer(texts.review_expired())
        return
    order = await db.get_order(db_path, order_id)
    if not order or order["user_id"] != callback.from_user.id:
        await callback.message.answer(texts.review_expired())
        return
    review = await db.create_review_request(db_path, order_id, order["user_id"], order["product_id"])
    if review["status"] != "pending":
        await callback.message.answer(texts.review_expired())
        return
    if callback.from_user.username:
        await db.update_review_contact(
            db_path,
            order_id,
            callback.from_user.id,
            username=callback.from_user.username,
        )
    try:
        await callback.message.edit_reply_markup()
    except Exception:
        pass
    await callback.message.answer(texts.review_contact_request(), reply_markup=build_review_contact_keyboard())


@router.message(F.contact)
async def handle_review_contact(message: Message):
    db_path = get_db_path(message.bot)
    user_state = await state_machine.get_user_state(db_path, message.from_user.id)
    if user_state != UserState.REVIEW_PENDING:
        return
    pending = await db.get_pending_review_for_user(db_path, message.from_user.id)
    if not pending:
        return
    phone = message.contact.phone_number if message.contact else None
    username = message.from_user.username
    await db.update_review_contact(
        db_path,
        pending["order_id"],
        message.from_user.id,
        phone=phone,
        username=username,
    )
    await message.answer("Можно писать отзыв.", reply_markup=remove_keyboard())
    await message.answer(texts.review_request(), reply_markup=build_review_cancel_keyboard())


@router.message(F.text == "⏭️ Пропустить")
async def handle_review_contact_skip(message: Message):
    db_path = get_db_path(message.bot)
    user_state = await state_machine.get_user_state(db_path, message.from_user.id)
    if user_state != UserState.REVIEW_PENDING:
        return
    pending = await db.get_pending_review_for_user(db_path, message.from_user.id)
    if not pending:
        return
    await message.answer(texts.review_contact_request(), reply_markup=build_review_contact_keyboard())


@router.callback_query(F.data.startswith("review:skip:"))
async def handle_review_skip(callback: CallbackQuery):
    order_id = (callback.data or "").split(":", maxsplit=2)[-1]
    await callback.answer()
    db_path = get_db_path(callback.bot)
    user_state = await state_machine.get_user_state(db_path, callback.from_user.id)
    if user_state != UserState.REVIEW_PENDING:
        await callback.message.answer(texts.review_expired())
        return
    user = await db.get_user(db_path, callback.from_user.id)
    if user and user.get("last_order_id") and user["last_order_id"] != order_id:
        await callback.message.answer(texts.review_expired())
        return
    order = await db.get_order(db_path, order_id)
    if not order or order["user_id"] != callback.from_user.id:
        await callback.message.answer(texts.review_expired())
        return
    review = await db.create_review_request(db_path, order_id, order["user_id"], order["product_id"])
    if review["status"] == "submitted":
        await callback.message.answer(texts.review_expired())
        return
    await db.mark_review_declined(db_path, order_id, order["user_id"], order["product_id"])
    try:
        await state_machine.set_reviewed(db_path, callback.from_user.id, order_id)
        await state_machine.ensure_idle(db_path, callback.from_user.id)
    except InvalidStateTransition:
        logger.warning("Skip review transition blocked user_id=%s order_id=%s", callback.from_user.id, order_id)
    try:
        await callback.message.edit_reply_markup()
    except Exception:
        pass


@router.callback_query(F.data.in_({REVIEW_CANCEL_CALLBACK, REVIEW_MENU_CALLBACK}))
async def handle_review_cancel(callback: CallbackQuery):
    await callback.answer()
    db_path = get_db_path(callback.bot)
    await state_machine.ensure_idle(db_path, callback.from_user.id)
    await callback.message.answer(texts.review_cancelled())
    from ..menu import show_catalog_menu

    await show_catalog_menu(callback.message)


@router.message(F.text)
async def handle_review_text(message: Message):
    if not message.text or message.text.startswith("/"):
        return
    review_text = message.text.strip()
    if not review_text:
        return
    db_path = get_db_path(message.bot)
    user_state = await state_machine.get_user_state(db_path, message.from_user.id)
    if user_state != UserState.REVIEW_PENDING:
        return
    if len(review_text) < 100:
        await message.answer(texts.review_request(), reply_markup=build_review_cancel_keyboard())
        return
    pending = await db.get_pending_review_for_user(db_path, message.from_user.id)
    if not pending:
        return
    if not pending.get("contact_phone"):
        await message.answer(texts.review_contact_request(), reply_markup=build_review_contact_keyboard())
        return
    if message.from_user.username:
        await db.update_review_contact(
            db_path,
            pending["order_id"],
            message.from_user.id,
            username=message.from_user.username,
        )
    await db.mark_review_submitted(db_path, pending["order_id"], review_text)
    parsed = parse_product(pending["product_id"])
    if parsed:
        reward_path = media.find_review_image(get_settings(message.bot).media_dir, parsed["sign"])
        if reward_path:
            caption = texts.review_reward_caption(parsed["sign"])
            await send_content(message.bot, message.chat.id, reward_path, caption)
    try:
        await state_machine.set_reviewed(db_path, message.from_user.id, pending["order_id"])
        await state_machine.ensure_idle(db_path, message.from_user.id)
    except InvalidStateTransition:
        logger.warning("Review submit transition blocked user_id=%s order_id=%s", message.from_user.id, pending["order_id"])
    await message.answer(texts.review_thanks(), reply_markup=remove_keyboard())

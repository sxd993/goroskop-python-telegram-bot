import asyncio
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.features import texts
from app.features.admin.dependencies import get_settings, is_admin
from app.features.admin.keyboards import (
    ADMIN_BROADCASTS_CALLBACK,
    ADMIN_BROADCAST_CREATE_CALLBACK,
    ADMIN_BROADCAST_LAUNCH_PREFIX,
    ADMIN_BROADCAST_RESPONSES_PREFIX,
    build_broadcasts_list_keyboard,
    build_broadcasts_menu_keyboard,
)
from app.features.admin.states import AdminBroadcastCreate
from app.features.user.keyboards import build_campaign_interest_keyboard
from app.services import db
from app.services.messaging import send_message_safe

logger = logging.getLogger(__name__)

router = Router()


def _ensure_admin(callback_or_message) -> bool:
    bot = callback_or_message.bot
    user = getattr(callback_or_message, "from_user", None)
    user_id = user.id if user else None  # type: ignore[attr-defined]
    return is_admin(bot, user_id)


def _format_campaign_button_text(item) -> str:
    title = item["title"]
    status = item["status"]
    created = item["created_at"][:16]
    return f"{title} · {status} · {created}"


@router.callback_query(F.data == ADMIN_BROADCASTS_CALLBACK)
async def handle_broadcasts_menu(callback: CallbackQuery, state: FSMContext):
    if not _ensure_admin(callback):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return

    await state.clear()
    await callback.answer()
    await callback.message.answer(
        texts.admin_broadcasts_menu(),
        reply_markup=build_broadcasts_menu_keyboard(),
    )


@router.callback_query(F.data == ADMIN_BROADCAST_CREATE_CALLBACK)
async def handle_broadcast_create_start(callback: CallbackQuery, state: FSMContext):
    if not _ensure_admin(callback):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return

    await state.set_state(AdminBroadcastCreate.title)
    await callback.answer()
    await callback.message.answer(texts.admin_broadcast_prompt_title())


@router.message(AdminBroadcastCreate.title)
async def handle_broadcast_title(message: Message, state: FSMContext):
    if not _ensure_admin(message):
        await state.clear()
        await message.answer(texts.admin_forbidden())
        return

    await state.update_data(title=message.text or "")
    await state.set_state(AdminBroadcastCreate.body)
    await message.answer(texts.admin_broadcast_prompt_body())


@router.message(AdminBroadcastCreate.body)
async def handle_broadcast_body(message: Message, state: FSMContext):
    if not _ensure_admin(message):
        await state.clear()
        await message.answer(texts.admin_forbidden())
        return

    await state.update_data(body=message.text or "")
    await state.set_state(AdminBroadcastCreate.price)
    await message.answer(texts.admin_broadcast_prompt_price())


def _parse_price_to_kopeks(text_value: str) -> int | None:
    try:
        cleaned = text_value.replace(" ", "").replace(",", ".")
        price_rub = float(cleaned)
        if price_rub < 0:
            return None
        return int(price_rub * 100)
    except Exception:
        return None


@router.message(AdminBroadcastCreate.price)
async def handle_broadcast_price(message: Message, state: FSMContext):
    if not _ensure_admin(message):
        await state.clear()
        await message.answer(texts.admin_forbidden())
        return

    price_kopeks = _parse_price_to_kopeks(message.text or "")
    if price_kopeks is None:
        await message.answer(texts.admin_broadcast_prompt_price())
        return

    data = await state.get_data()
    title = data.get("title", "").strip() or "Без названия"
    body = data.get("body", "").strip() or ""

    await state.clear()

    campaign = await db.create_campaign(
        get_settings(message.bot).db_path,
        title,
        body,
        price_kopeks,
    )

    await message.answer(
        texts.admin_broadcast_created(title),
        reply_markup=build_broadcasts_menu_keyboard(),
    )

    logger.info("Campaign created id=%s title=%s", campaign["id"], campaign["title"])


@router.callback_query(F.data.startswith(f"{ADMIN_BROADCAST_LAUNCH_PREFIX}:"))
async def handle_broadcast_launch(callback: CallbackQuery, state: FSMContext):
    if not _ensure_admin(callback):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return

    await state.clear()
    action = (callback.data or "").split(":", maxsplit=3)[-1]
    db_path = get_settings(callback.bot).db_path

    if action == "list":
        campaigns = await db.list_campaigns(db_path, statuses=["draft"])
        if not campaigns:
            await callback.answer()
            await callback.message.answer(
                texts.admin_broadcasts_empty(),
                reply_markup=build_broadcasts_menu_keyboard(),
            )
            return

        await callback.answer()
        await callback.message.answer(
            "Выбери рассылку для запуска:",
            reply_markup=build_broadcasts_list_keyboard(
                [(_format_campaign_button_text(item), item["id"]) for item in campaigns],
                prefix=ADMIN_BROADCAST_LAUNCH_PREFIX,
            ),
        )
        return

    campaign_id = action
    campaign = await db.get_campaign(db_path, campaign_id)
    if not campaign:
        await callback.answer("Рассылка не найдена", show_alert=True)
        return

    audience = await db.fetch_paid_user_ids(db_path)
    if not audience:
        await callback.answer()
        await callback.message.answer(
            "Нет аудитории с оплаченными заказами.",
            reply_markup=build_broadcasts_menu_keyboard(),
        )
        return

    await db.add_campaign_audience(db_path, campaign_id, audience)
    await db.update_campaign_status(db_path, campaign_id, "running")

    await callback.answer()
    await callback.message.answer(
        texts.admin_broadcast_launch_started(campaign["title"], len(audience))
    )

    async def _send():
        sent = failed = 0
        interested = declined = 0

        for user_id in audience:
            try:
                text = texts.campaign_offer(
                    campaign["body"],
                    campaign["price_kopeks"] / 100,
                )

                msg = await send_message_safe(
                    callback.bot,
                    user_id,
                    text,
                    reply_markup=build_campaign_interest_keyboard(campaign_id),
                )

                message_id = getattr(msg, "message_id", None)

                if message_id is not None:
                    sent += 1
                    await db.update_campaign_audience_status(
                        db_path,
                        campaign_id,
                        user_id,
                        "sent",
                        message_id=message_id,
                    )
                else:
                    failed += 1
                    await db.update_campaign_audience_status(
                        db_path,
                        campaign_id,
                        user_id,
                        "failed",
                        error="Delivery failed",
                    )

            except Exception as exc:
                logger.exception(
                    "Campaign send failed user_id=%s campaign_id=%s",
                    user_id,
                    campaign_id,
                )
                failed += 1
                await db.update_campaign_audience_status(
                    db_path,
                    campaign_id,
                    user_id,
                    "failed",
                    error=str(exc),
                )

            await asyncio.sleep(0.05)

        audience_rows = await db.get_campaign_audience(db_path, campaign_id)
        for row in audience_rows:
            if row["status"] == "interested":
                interested += 1
            elif row["status"] == "declined":
                declined += 1

        await db.update_campaign_status(db_path, campaign_id, "completed")

        await send_message_safe(
            callback.bot,
            callback.message.chat.id,
            texts.admin_broadcast_launch_finished(
                sent,
                failed,
                interested,
                declined,
            ),
            reply_markup=build_broadcasts_menu_keyboard(),
        )

    asyncio.create_task(_send())


@router.callback_query(F.data.startswith(f"{ADMIN_BROADCAST_RESPONSES_PREFIX}:"))
async def handle_broadcast_responses(callback: CallbackQuery, state: FSMContext):
    if not _ensure_admin(callback):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return

    await state.clear()
    action = (callback.data or "").split(":", maxsplit=3)[-1]
    db_path = get_settings(callback.bot).db_path

    if action == "list":
        campaigns = await db.list_campaigns(db_path)
        if not campaigns:
            await callback.answer()
            await callback.message.answer(
                texts.admin_broadcasts_empty(),
                reply_markup=build_broadcasts_menu_keyboard(),
            )
            return

        await callback.answer()
        await callback.message.answer(
            "Выбери рассылку для просмотра ответов:",
            reply_markup=build_broadcasts_list_keyboard(
                [(_format_campaign_button_text(item), item["id"]) for item in campaigns],
                prefix=ADMIN_BROADCAST_RESPONSES_PREFIX,
            ),
        )
        return

    campaign_id = action
    campaign = await db.get_campaign(db_path, campaign_id)
    if not campaign:
        await callback.answer("Рассылка не найдена", show_alert=True)
        return

    responses = await db.list_campaign_responses(db_path, campaign_id)
    if not responses:
        await callback.answer()
        await callback.message.answer(
            texts.admin_broadcast_responses_empty(),
            reply_markup=build_broadcasts_menu_keyboard(),
        )
        return

    lines = [texts.admin_broadcast_responses_title(campaign["title"])]
    for resp in responses:
        lines.append(
            "\n".join(
                [
                    f"User: {resp['user_id']}",
                    f"ФИО: {resp.get('full_name') or '-'}",
                    f"Дата: {resp.get('birthdate') or '-'}",
                    f"Телефон: {resp.get('phone') or '-'}",
                    f"Комментарий: {resp.get('raw_text') or '-'}",
                    f"Статус: {resp.get('status')}",
                ]
            )
        )
        lines.append("—" * 10)

    await callback.answer()
    await callback.message.answer(
        "\n\n".join(lines),
        reply_markup=build_broadcasts_menu_keyboard(),
    )

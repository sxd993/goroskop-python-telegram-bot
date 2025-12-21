import asyncio
import logging
import secrets

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import texts
from app.features.admin.dependencies import get_settings, is_admin
from app.features.admin.keyboards import (
    ADMIN_BROADCASTS_CALLBACK,
    ADMIN_BROADCAST_CREATE_CALLBACK,
    ADMIN_BROADCAST_DELETE_PREFIX,
    ADMIN_BROADCAST_ITEM_PREFIX,
    ADMIN_BROADCAST_LIST_CALLBACK,
    ADMIN_BROADCAST_LAUNCH_PREFIX,
    ADMIN_BROADCAST_RESPONSES_PREFIX,
    ADMIN_BROADCAST_RESPONSES_ITEM_PREFIX,
    build_broadcast_item_menu_keyboard,
    build_broadcast_responses_list_keyboard,
    build_broadcast_response_detail_keyboard,
    build_broadcasts_list_keyboard,
    build_broadcasts_menu_keyboard,
)
from app.features.admin.states import AdminBroadcastCreate
from app.features.user.keyboards import build_campaign_interest_keyboard
from app.services import db
from app.services.messaging import send_message_safe

logger = logging.getLogger(__name__)

router = Router()


_campaign_token_map: dict[str, str] = {}
_campaign_token_reverse: dict[str, str] = {}
_response_token_map: dict[str, tuple[str, str]] = {}


def _ensure_admin(callback_or_message) -> bool:
    bot = callback_or_message.bot
    user = getattr(callback_or_message, "from_user", None)
    user_id = user.id if user else None  # type: ignore[attr-defined]
    return is_admin(bot, user_id)


def _format_campaign_button_text(item) -> str:
    return item["title"]


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


RESPONSES_PAGE_SIZE = 5


def _get_campaign_token(campaign_id: str) -> str:
    existing = _campaign_token_reverse.get(campaign_id)
    if existing:
        return existing
    token = secrets.token_hex(4)
    _campaign_token_map[token] = campaign_id
    _campaign_token_reverse[campaign_id] = token
    return token


def _resolve_campaign_token(token: str) -> str:
    return _campaign_token_map.get(token, "")


def _register_response_token(campaign_id: str, response_id: str) -> str:
    token = response_id[:8]
    if token in _response_token_map and _response_token_map[token] != (campaign_id, response_id):
        token = secrets.token_hex(4)
    _response_token_map[token] = (campaign_id, response_id)
    return token


def _resolve_response_token(token: str) -> tuple[str, str]:
    return _response_token_map.get(token, ("", ""))




def _parse_responses_list_payload(data: str) -> tuple[str, str, int]:
    if not data or not data.startswith(f"{ADMIN_BROADCAST_RESPONSES_PREFIX}:"):
        return "", "", 1
    suffix = data[len(ADMIN_BROADCAST_RESPONSES_PREFIX) + 1 :]
    if not suffix:
        return "", "", 1
    parts = suffix.split(":")
    page = 1
    if len(parts) > 1:
        try:
            page = int(parts[1])
        except ValueError:
            page = 1
    key = parts[0]
    if key in _campaign_token_map:
        campaign_token = key
        campaign_id = _campaign_token_map[key]
        return campaign_id, campaign_token, max(1, page)
    campaign_id = key
    campaign_token = _get_campaign_token(campaign_id)
    return campaign_id, campaign_token, max(1, page)


def _parse_response_detail_payload(data: str) -> tuple[str, int, str]:
    if not data or not data.startswith(f"{ADMIN_BROADCAST_RESPONSES_ITEM_PREFIX}:"):
        return "", 1, ""
    suffix = data[len(ADMIN_BROADCAST_RESPONSES_ITEM_PREFIX) + 1 :]
    parts = suffix.split(":")
    if len(parts) < 3:
        return "", 1, ""
    campaign_token = parts[0]
    try:
        page = int(parts[1])
    except ValueError:
        page = 1
    response_token = parts[2]
    campaign_id = _resolve_campaign_token(campaign_token)
    return campaign_id, max(1, page), response_token


@router.callback_query(F.data == ADMIN_BROADCAST_LIST_CALLBACK)
async def handle_broadcasts_list(callback: CallbackQuery, state: FSMContext):
    if not _ensure_admin(callback):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return

    logger.info("Admin broadcast list opened by user=%s", callback.from_user.id)

    await state.clear()
    await callback.answer()
    db_path = get_settings(callback.bot).db_path

    campaigns = await db.list_campaigns(db_path)
    if not campaigns:
        await callback.message.answer(
            texts.admin_broadcasts_empty(),
            reply_markup=build_broadcasts_menu_keyboard(),
        )
        return

    await callback.message.answer(
        texts.admin_broadcasts_list_title(),
        reply_markup=build_broadcasts_list_keyboard(
            [(_format_campaign_button_text(item), item["id"]) for item in campaigns],
            prefix=ADMIN_BROADCAST_ITEM_PREFIX,
        ),
    )


@router.callback_query(F.data.startswith(f"{ADMIN_BROADCAST_ITEM_PREFIX}:"))
async def handle_broadcast_item_select(callback: CallbackQuery, state: FSMContext):
    if not _ensure_admin(callback):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return

    logger.info("Admin opened broadcast card user=%s data=%s", callback.from_user.id, callback.data)

    await state.clear()
    await callback.answer()
    campaign_id = (callback.data or "").rsplit(":", 1)[-1]
    db_path = get_settings(callback.bot).db_path

    campaign = await db.get_campaign(db_path, campaign_id)
    if not campaign:
        await callback.answer("Рассылка не найдена", show_alert=True)
        return

    price_rub = campaign["price_kopeks"] / 100

    await callback.message.answer(
        texts.admin_broadcast_item_detail(
            campaign["title"],
            price_rub,
        ),
        reply_markup=build_broadcast_item_menu_keyboard(campaign_id),
    )


@router.callback_query(F.data.startswith(f"{ADMIN_BROADCAST_DELETE_PREFIX}:"))
async def handle_broadcast_delete(callback: CallbackQuery, state: FSMContext):
    if not _ensure_admin(callback):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return

    await state.clear()
    await callback.answer()
    campaign_id = (callback.data or "").split(":", maxsplit=3)[-1]
    db_path = get_settings(callback.bot).db_path

    campaign = await db.get_campaign(db_path, campaign_id)
    if not campaign:
        await callback.answer("Рассылка не найдена", show_alert=True)
        return

    await db.delete_campaign(db_path, campaign_id)
    logger.info("Campaign deleted id=%s title=%s", campaign_id, campaign["title"])

    await callback.message.answer(
        texts.admin_broadcast_deleted(campaign["title"]),
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
    campaign_id = (callback.data or "").split(":", maxsplit=3)[-1]
    db_path = get_settings(callback.bot).db_path

    campaign = await db.get_campaign(db_path, campaign_id)
    if not campaign:
        await callback.answer("Рассылка не найдена", show_alert=True)
        return

    if await db.campaign_has_audience(db_path, campaign_id):
        await callback.answer("Рассылка уже запущена", show_alert=True)
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

    await callback.answer()
    await callback.message.answer(texts.admin_broadcast_launch_ack())

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

    asyncio.create_task(_send())


@router.callback_query(F.data.startswith(f"{ADMIN_BROADCAST_RESPONSES_PREFIX}:"))
async def handle_broadcast_responses(callback: CallbackQuery, state: FSMContext):
    if not _ensure_admin(callback):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return

    await state.clear()
    campaign_id, campaign_token, page = _parse_responses_list_payload(callback.data or "")
    if not campaign_id:
        await callback.answer("Рассылка не найдена", show_alert=True)
        return

    db_path = get_settings(callback.bot).db_path
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

    total_pages = max(1, (len(responses) + RESPONSES_PAGE_SIZE - 1) // RESPONSES_PAGE_SIZE)
    page = min(max(page, 1), total_pages)
    start = (page - 1) * RESPONSES_PAGE_SIZE
    chunk = responses[start : start + RESPONSES_PAGE_SIZE]
    for resp in chunk:
        resp["_token"] = _register_response_token(campaign_id, resp["id"])

    await callback.answer()
    await callback.message.answer(
        texts.admin_broadcast_responses_list_title(campaign["title"], page, total_pages),
        reply_markup=build_broadcast_responses_list_keyboard(
            campaign_id,
            campaign_token,
            chunk,
            page=page,
            has_next=page < total_pages,
        ),
    )


@router.callback_query(F.data.startswith(f"{ADMIN_BROADCAST_RESPONSES_ITEM_PREFIX}:"))
async def handle_broadcast_response_detail(callback: CallbackQuery, state: FSMContext):
    if not _ensure_admin(callback):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return

    await state.clear()
    campaign_id, page, response_token = _parse_response_detail_payload(callback.data or "")
    if not campaign_id or not response_token:
        await callback.answer("Данные ответа не найдены", show_alert=True)
        return

    db_path = get_settings(callback.bot).db_path
    campaign = await db.get_campaign(db_path, campaign_id)
    if not campaign:
        await callback.answer("Рассылка не найдена", show_alert=True)
        return

    response_campaign_id, response_id = _resolve_response_token(response_token)
    if response_campaign_id != campaign_id or not response_id:
        await callback.answer("Ответ не найден", show_alert=True)
        return

    responses = await db.list_campaign_responses(db_path, campaign_id)
    response = next((item for item in responses if item["id"] == response_id), None)
    if not response:
        await callback.answer("Ответ не найден", show_alert=True)
        return

    campaign_token = _get_campaign_token(campaign_id)
    await callback.answer()
    await callback.message.answer(
        texts.admin_broadcast_response_detail(campaign["title"], response),
        reply_markup=build_broadcast_response_detail_keyboard(
            campaign_id=campaign_id,
            campaign_token=campaign_token,
            page=page,
        ),
    )

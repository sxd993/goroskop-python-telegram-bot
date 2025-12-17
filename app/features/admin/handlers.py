import datetime as dt
import logging
from pathlib import Path
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import texts
from app.config import Settings, SIGNS_RU
from app.features.admin.keyboards import (
    ADMIN_ADD_FORECAST_CALLBACK,
    ADMIN_BACK_MENU_CALLBACK,
    ADMIN_DELETE_FORECAST_CALLBACK,
    ADMIN_REVIEWS_CALLBACK,
    ADMIN_STATS_CALLBACK,
    ADMIN_REVIEW_IMAGE_CALLBACK,
    ADMIN_REVIEWS_PAGE_PREFIX,
    ADMIN_REVIEW_OPEN_PREFIX,
    build_admin_delete_confirm_keyboard,
    build_admin_menu,
    build_admin_years_keyboard,
    build_admin_months_keyboard,
    build_admin_type_keyboard,
    build_admin_signs_keyboard,
    build_admin_reviews_list_keyboard,
    build_admin_review_detail_keyboard,
)
from app.services import media, db
from app.services.parsing import parse_product

logger = logging.getLogger(__name__)

router = Router()

_settings: Settings | None = None


class AdminUpload(StatesGroup):
    kind = State()
    year = State()
    month = State()
    sign = State()
    file = State()


class AdminDelete(StatesGroup):
    kind = State()
    year = State()
    month = State()
    sign = State()
    confirm = State()


class AdminReviewImage(StatesGroup):
    sign = State()
    file = State()


REVIEWS_PAGE_SIZE = 5


def setup_handlers(settings: Settings) -> None:
    global _settings
    _settings = settings


def get_settings(bot: Bot) -> Settings:
    if _settings is None:
        raise RuntimeError("Handlers are not configured with settings")
    return _settings


def is_admin(bot: Bot, user_id: Optional[int]) -> bool:
    settings = get_settings(bot)
    return bool(user_id and user_id in settings.admin_ids)


def _product_label(product_id: str) -> str:
    parsed = parse_product(product_id)
    if not parsed:
        return product_id
    sign_name = SIGNS_RU.get(parsed["sign"], parsed["sign"])
    if parsed["kind"] == "month" and parsed["month"]:
        ym = f"{parsed['year']}-{parsed['month']}"
        month_name = media.month_name_from_ym(ym) or ym
        return f"{month_name} {parsed['year']}, {sign_name}"
    return f"{parsed['year']} год, {sign_name}"


def _format_dt(value: str) -> str:
    try:
        return dt.datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return value


async def _edit_or_send(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    try:
        if callback.message:
            await callback.message.edit_text(text, reply_markup=reply_markup)
            return
    except Exception:
        logger.exception("Failed to edit message for callback")
    if callback.message:
        await callback.message.answer(text, reply_markup=reply_markup)


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
            await _edit_or_send(callback, texts.admin_reviews_empty(), reply_markup=build_admin_menu())
        return

    has_next = len(raw) > REVIEWS_PAGE_SIZE
    reviews = raw[:REVIEWS_PAGE_SIZE]
    items: list[tuple[str, str]] = []
    for idx, review in enumerate(reviews, start=1):
        status = review["status"]
        icon = "✅" if status == "submitted" else "🚫"
        created = _format_dt(review["created_at"])
        order_tag = review["order_id"][:8]
        title = _product_label(review["product_id"])
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
    await _edit_or_send(callback, texts.admin_reviews_page_title(page), reply_markup=markup)


@router.message(Command("admin"))
async def handle_admin_entry(message: Message, state: FSMContext):
    if not is_admin(message.bot, message.from_user.id):
        await state.clear()
        await message.answer(texts.admin_forbidden())
        return
    await state.clear()
    await message.answer(texts.admin_menu(), reply_markup=build_admin_menu())


@router.callback_query(F.data == ADMIN_ADD_FORECAST_CALLBACK)
async def handle_admin_add(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminUpload.kind)
    await callback.answer()
    await callback.message.answer(texts.admin_choose_type(), reply_markup=build_admin_type_keyboard())


@router.callback_query(F.data == ADMIN_DELETE_FORECAST_CALLBACK)
async def handle_admin_delete(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminDelete.kind)
    await callback.answer()
    await callback.message.answer(texts.admin_delete_start(), reply_markup=build_admin_type_keyboard())


@router.callback_query(F.data == ADMIN_STATS_CALLBACK)
async def handle_admin_stats(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    stats = await db.fetch_sales_stats(get_settings(callback.bot).db_path)
    if not stats:
        await callback.answer()
        await callback.message.answer(texts.admin_stats_empty())
        return
    lines = [texts.admin_stats_title()]
    for product_id, count, total in stats:
        parsed = parse_product(product_id)
        if not parsed:
            continue
        sign_name = SIGNS_RU.get(parsed["sign"], parsed["sign"])
        if parsed["kind"] == "month" and parsed["month"]:
            ym = f"{parsed['year']}-{parsed['month']}"
            month_name = media.month_name_from_ym(ym) or ym
            label = f"{month_name} {parsed['year']}, {sign_name}"
        else:
            label = f"{parsed['year']} год, {sign_name}"
        lines.append(f"{label}: {count} шт. / {total/100:.0f} ₽")
    await callback.answer()
    await callback.message.answer("\n".join(lines))


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

    created = _format_dt(review["created_at"])
    order_tag = review["order_id"][:8]
    title = _product_label(review["product_id"])
    text = review.get("text") or "—"
    await callback.answer()
    await _edit_or_send(
        callback,
        texts.admin_review_detail(
            title=title,
            created=created,
            order_tag=order_tag,
            user_id=review["user_id"],
            status=review["status"],
            text=text,
        ),
        reply_markup=build_admin_review_detail_keyboard(page=page),
    )


@router.callback_query(F.data == ADMIN_BACK_MENU_CALLBACK)
async def handle_admin_back_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    await callback.answer()
    await callback.message.answer(texts.admin_menu(), reply_markup=build_admin_menu())


@router.callback_query(F.data == ADMIN_REVIEW_IMAGE_CALLBACK)
async def handle_admin_review_image(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminReviewImage.sign)
    await callback.answer()
    await callback.message.answer(texts.admin_review_image_start(), reply_markup=build_admin_signs_keyboard())


@router.callback_query(AdminReviewImage.sign, F.data.startswith("admin-sign:"))
async def handle_admin_review_image_sign(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await state.clear()
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    sign = (callback.data or "").split(":", maxsplit=1)[-1]
    if sign not in SIGNS_RU:
        await callback.answer(texts.admin_invalid_sign(), show_alert=True)
        return
    await state.update_data(sign=sign)
    await state.set_state(AdminReviewImage.file)
    await callback.answer()
    await callback.message.answer(texts.admin_review_image_prompt(sign))


def _review_destination_path(media_dir: Path, sign: str, extension: str) -> Path:
    target_dir = media_dir / "reviews" / sign
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{sign}.{extension}"


@router.message(AdminReviewImage.file)
async def handle_admin_review_image_file(message: Message, state: FSMContext):
    if not is_admin(message.bot, message.from_user.id):
        await state.clear()
        await message.answer(texts.admin_forbidden())
        return
    extension = _detect_extension(message)
    if not extension or extension not in media.ALLOWED_EXTENSIONS:
        await message.answer(texts.admin_invalid_file())
        return
    data = await state.get_data()
    sign = data.get("sign")
    settings = get_settings(message.bot)
    if not sign:
        await state.clear()
        await message.answer(texts.admin_session_reset())
        return
    destination = _review_destination_path(settings.media_dir, sign, extension)
    for ext in media.ALLOWED_EXTENSIONS:
        existing = destination.with_suffix(f".{ext}")
        if existing.exists():
            existing.unlink()
    success = await _save_media(message, destination)
    if not success:
        await message.answer(texts.admin_save_failed())
        return
    await state.clear()
    await message.answer(texts.admin_review_image_saved(sign))
    await message.answer(texts.admin_menu(), reply_markup=build_admin_menu())


@router.callback_query(AdminUpload.kind, F.data.startswith("admin-type:"))
async def handle_admin_type(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await state.clear()
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    kind = (callback.data or "").split(":", maxsplit=1)[-1]
    if kind not in {"year", "month"}:
        await callback.answer(texts.admin_invalid_type(), show_alert=True)
        return
    await state.update_data(kind=kind)
    await state.set_state(AdminUpload.year)
    await callback.answer()
    await callback.message.answer(texts.admin_prompt_year())


@router.callback_query(AdminDelete.kind, F.data.startswith("admin-type:"))
async def handle_admin_delete_type(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await state.clear()
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    kind = (callback.data or "").split(":", maxsplit=1)[-1]
    if kind not in {"year", "month"}:
        await callback.answer(texts.admin_invalid_type(), show_alert=True)
        return
    await state.update_data(kind=kind)
    settings = get_settings(callback.bot)
    if kind == "year":
        years = media.available_yearly_years(settings.media_dir)
        if not years:
            await state.clear()
            await callback.answer()
            await callback.message.answer(texts.admin_delete_no_years())
            return
        await state.set_state(AdminDelete.year)
        await callback.answer()
        await callback.message.answer(
            texts.admin_choose_year_delete_year(),
            reply_markup=build_admin_years_keyboard(years, prefix="admin-del-y-year"),
        )
    else:
        years = media.available_monthly_years(settings.media_dir)
        if not years:
            await state.clear()
            await callback.answer()
            await callback.message.answer(texts.admin_delete_no_month_years())
            return
        await state.set_state(AdminDelete.year)
        await callback.answer()
        await callback.message.answer(
            texts.admin_choose_year_delete_month(),
            reply_markup=build_admin_years_keyboard(years, prefix="admin-del-m-year"),
        )


@router.message(AdminUpload.year)
async def handle_admin_year(message: Message, state: FSMContext):
    if not is_admin(message.bot, message.from_user.id):
        await state.clear()
        await message.answer(texts.admin_forbidden())
        return
    data = await state.get_data()
    kind = data.get("kind")
    if kind not in {"year", "month"}:
        await state.clear()
        await message.answer(texts.admin_session_reset())
        return
    if not message.text:
        await message.answer(texts.admin_invalid_year())
        return
    year = message.text.strip()
    if not media.is_valid_year(year):
        await message.answer(texts.admin_invalid_year())
        return
    await state.update_data(year=year)
    if kind == "year":
        await state.set_state(AdminUpload.sign)
        await message.answer(texts.admin_choose_sign_year(year), reply_markup=build_admin_signs_keyboard())
    else:
        await state.set_state(AdminUpload.month)
        await message.answer(texts.admin_choose_month(year), reply_markup=build_admin_months_keyboard())


@router.callback_query(AdminDelete.year, F.data.startswith("admin-del-y-year:"))
async def handle_admin_delete_year_choose(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await state.clear()
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    year = (callback.data or "").split(":", maxsplit=1)[-1]
    settings = get_settings(callback.bot)
    if year not in media.available_yearly_years(settings.media_dir):
        await callback.answer(texts.year_unavailable(), show_alert=True)
        return
    signs = media.available_year_signs(settings.media_dir, year)
    if not signs:
        await state.clear()
        await callback.answer()
        await callback.message.answer(texts.admin_delete_no_signs())
        await callback.message.answer(texts.admin_menu(), reply_markup=build_admin_menu())
        return
    await state.update_data(year=year)
    await state.set_state(AdminDelete.sign)
    await callback.answer()
    await callback.message.answer(
        texts.admin_choose_sign_delete_year(year),
        reply_markup=build_admin_signs_keyboard(signs),
    )


@router.callback_query(AdminDelete.year, F.data.startswith("admin-del-m-year:"))
async def handle_admin_delete_month_year_choose(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await state.clear()
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    year = (callback.data or "").split(":", maxsplit=1)[-1]
    settings = get_settings(callback.bot)
    if year not in media.available_monthly_years(settings.media_dir):
        await callback.answer(texts.year_unavailable(), show_alert=True)
        return
    months = media.months_for_year(settings.media_dir, year)
    if not months:
        await state.clear()
        await callback.answer()
        await callback.message.answer(texts.admin_delete_no_months(year))
        await callback.message.answer(texts.admin_menu(), reply_markup=build_admin_menu())
        return
    month_ints = [int(m.split("-")[1]) for m in months]
    await state.update_data(year=year)
    await state.set_state(AdminDelete.month)
    await callback.answer()
    await callback.message.answer(
        texts.admin_choose_month_delete(year),
        reply_markup=build_admin_months_keyboard(month_ints),
    )


@router.callback_query(AdminUpload.month, F.data.startswith("admin-month:"))
async def handle_admin_month(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await state.clear()
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    data = await state.get_data()
    if data.get("kind") != "month":
        await state.clear()
        await callback.answer(texts.admin_session_reset(), show_alert=True)
        return
    raw_month = (callback.data or "").split(":", maxsplit=1)[-1]
    try:
        month_int = int(raw_month)
    except ValueError:
        await callback.answer(texts.admin_invalid_month(), show_alert=True)
        return
    if month_int < 1 or month_int > 12:
        await callback.answer(texts.admin_invalid_month(), show_alert=True)
        return
    month = f"{month_int:02d}"
    year = data.get("year")
    if not year:
        await state.clear()
        await callback.message.answer(texts.admin_session_reset())
        await callback.answer()
        return
    await state.update_data(month=month)
    await state.set_state(AdminUpload.sign)
    await callback.answer()
    await callback.message.answer(
        texts.admin_choose_sign(year, month), reply_markup=build_admin_signs_keyboard()
    )


@router.callback_query(AdminDelete.month, F.data.startswith("admin-month:"))
async def handle_admin_delete_month(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await state.clear()
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    data = await state.get_data()
    if data.get("kind") != "month":
        await state.clear()
        await callback.answer(texts.admin_session_reset(), show_alert=True)
        return
    raw_month = (callback.data or "").split(":", maxsplit=1)[-1]
    try:
        month_int = int(raw_month)
    except ValueError:
        await callback.answer(texts.admin_invalid_month(), show_alert=True)
        return
    if month_int < 1 or month_int > 12:
        await callback.answer(texts.admin_invalid_month(), show_alert=True)
        return
    month = f"{month_int:02d}"
    year = data.get("year")
    if not year:
        await state.clear()
        await callback.message.answer(texts.admin_session_reset())
        await callback.answer()
        return
    await state.update_data(month=month)
    await state.set_state(AdminDelete.sign)
    await callback.answer()
    settings = get_settings(callback.bot)
    ym = f"{year}-{month}"
    signs = media.available_month_signs(settings.media_dir, ym)
    if not signs:
        await state.clear()
        await callback.message.answer(texts.admin_delete_no_signs())
        await callback.message.answer(texts.admin_menu(), reply_markup=build_admin_menu())
        return
    await callback.message.answer(
        texts.admin_choose_sign_delete_month(year, month), reply_markup=build_admin_signs_keyboard(signs)
    )


@router.callback_query(AdminDelete.confirm, F.data.startswith("admin-del-confirm:"))
async def handle_admin_delete_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await state.clear()
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    data = await state.get_data()
    kind = data.get("kind")
    year = data.get("year")
    month = data.get("month")
    sign = data.get("sign")
    parts = (callback.data or "").split(":")
    if len(parts) < 4:
        await state.clear()
        await callback.answer(texts.admin_session_reset(), show_alert=True)
        return
    decision = parts[-1]
    if decision == "no":
        await state.clear()
        await callback.answer()
        await callback.message.answer(texts.admin_delete_cancelled(), reply_markup=build_admin_menu())
        return
    if kind not in {"year", "month"} or not year or not sign or decision != "yes":
        await state.clear()
        await callback.answer(texts.admin_session_reset(), show_alert=True)
        return
    settings = get_settings(callback.bot)
    await state.clear()
    if kind == "year":
        success = media.delete_year_content(settings.media_dir, year, sign)
        text = texts.admin_delete_success_year(year, sign) if success else texts.admin_delete_missing()
    else:
        if not month:
            await callback.answer(texts.admin_session_reset(), show_alert=True)
            return
        ym = f"{year}-{month}"
        success = media.delete_month_content(settings.media_dir, ym, sign)
        text = texts.admin_delete_success_month(year, month, sign) if success else texts.admin_delete_missing()
    await callback.answer()
    await callback.message.answer(text)
    await callback.message.answer(texts.admin_menu(), reply_markup=build_admin_menu())


@router.callback_query(AdminUpload.sign, F.data.startswith("admin-sign:"))
async def handle_admin_sign(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await state.clear()
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    sign = (callback.data or "").split(":", maxsplit=1)[-1]
    if sign not in SIGNS_RU:
        await callback.answer(texts.admin_invalid_sign(), show_alert=True)
        return
    data = await state.get_data()
    kind = data.get("kind")
    year = data.get("year")
    month = data.get("month")
    if not year or not kind:
        await state.clear()
        await callback.message.answer(texts.admin_session_reset())
        await callback.answer()
        return
    await state.update_data(sign=sign)
    await state.set_state(AdminUpload.file)
    await callback.answer()
    if kind == "year":
        await callback.message.answer(texts.admin_prompt_file_year(year, sign))
    else:
        if not month:
            await state.clear()
            await callback.message.answer(texts.admin_session_reset())
            return
        await callback.message.answer(texts.admin_prompt_file_month(year, month, sign))


@router.callback_query(AdminDelete.sign, F.data.startswith("admin-sign:"))
async def handle_admin_delete_sign(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await state.clear()
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    sign = (callback.data or "").split(":", maxsplit=1)[-1]
    if sign not in SIGNS_RU:
        await callback.answer(texts.admin_invalid_sign(), show_alert=True)
        return
    data = await state.get_data()
    kind = data.get("kind")
    year = data.get("year")
    month = data.get("month")
    settings = get_settings(callback.bot)
    if kind not in {"year", "month"} or not year:
        await state.clear()
        await callback.message.answer(texts.admin_session_reset())
        await callback.answer()
        return
    await state.update_data(sign=sign)
    await state.set_state(AdminDelete.confirm)
    await callback.answer()
    if kind == "year":
        text = texts.admin_delete_confirm_year(year, sign)
        action = f"admin-del-confirm:year:{year}:{sign}"
    else:
        if not month:
            await state.clear()
            await callback.message.answer(texts.admin_session_reset())
            return
        text = texts.admin_delete_confirm_month(year, month, sign)
        action = f"admin-del-confirm:month:{year}-{month}:{sign}"
    await callback.message.answer(text, reply_markup=build_admin_delete_confirm_keyboard(action))


def _detect_extension(message: Message) -> Optional[str]:
    if message.document and message.document.file_name:
        parts = message.document.file_name.rsplit(".", maxsplit=1)
        if len(parts) == 2:
            return parts[-1].lower()
    if message.photo:
        return "jpg"
    return None


def _destination_path(kind: str, media_dir: Path, year: str, sign: str, extension: str, month: str | None) -> Path:
    if kind == "year":
        target_dir = media_dir / "year" / year
    else:
        target_dir = media_dir / "month" / year / (month or "01")
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{sign}.{extension}"


async def _save_media(message: Message, destination: Path) -> bool:
    if not message.document and not message.photo:
        return False
    file_to_download = message.document or message.photo[-1]
    try:
        await message.bot.download(file_to_download, destination=destination)
        return True
    except Exception:
        logger.exception("Failed to download media to %s", destination)
        return False


@router.message(AdminUpload.file)
async def handle_admin_file(message: Message, state: FSMContext):
    if not is_admin(message.bot, message.from_user.id):
        await state.clear()
        await message.answer(texts.admin_forbidden())
        return
    extension = _detect_extension(message)
    if not extension or extension not in media.ALLOWED_EXTENSIONS:
        await message.answer(texts.admin_invalid_file())
        return
    data = await state.get_data()
    kind = data.get("kind")
    year = data.get("year")
    month = data.get("month")
    sign = data.get("sign")
    settings = get_settings(message.bot)
    if kind not in {"year", "month"} or not year or not sign:
        await state.clear()
        await message.answer(texts.admin_session_reset())
        return
    if kind == "month" and not month:
        await state.clear()
        await message.answer(texts.admin_session_reset())
        return
    destination = _destination_path(kind, settings.media_dir, year, sign, extension, month)
    for ext in media.ALLOWED_EXTENSIONS:
        existing = destination.with_suffix(f".{ext}")
        if existing.exists():
            existing.unlink()
    success = await _save_media(message, destination)
    if not success:
        await message.answer(texts.admin_save_failed())
        return
    await state.clear()
    if kind == "year":
        await message.answer(texts.admin_save_success_year(year, sign))
    else:
        await message.answer(texts.admin_save_success_month(year, month, sign))
    await message.answer(texts.admin_menu(), reply_markup=build_admin_menu())

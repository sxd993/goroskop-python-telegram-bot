from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.features import texts
from app.config import SIGNS_RU
from app.features.admin.dependencies import get_settings, is_admin
from app.features.admin.keyboards import (
    ADMIN_ADD_FORECAST_CALLBACK,
    ADMIN_DELETE_FORECAST_CALLBACK,
    build_admin_delete_confirm_keyboard,
    build_admin_menu,
    build_admin_months_keyboard,
    build_admin_signs_keyboard,
    build_admin_type_keyboard,
    build_admin_years_keyboard,
)
from app.features.admin.states import AdminDelete, AdminUpload
from app.features.admin.utils import destination_path, detect_extension, save_media
from app.services import media

router = Router()


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


@router.message(AdminUpload.file)
async def handle_admin_file(message: Message, state: FSMContext):
    if not is_admin(message.bot, message.from_user.id):
        await state.clear()
        await message.answer(texts.admin_forbidden())
        return
    extension = detect_extension(message)
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
    destination = destination_path(kind, settings.media_dir, year, sign, extension, month)
    for ext in media.ALLOWED_EXTENSIONS:
        existing = destination.with_suffix(f".{ext}")
        if existing.exists():
            existing.unlink()
    success = await save_media(message, destination)
    if not success:
        await message.answer(texts.admin_save_failed())
        return
    await state.clear()
    if kind == "year":
        await message.answer(texts.admin_save_success_year(year, sign))
    else:
        await message.answer(texts.admin_save_success_month(year, month, sign))
    await message.answer(texts.admin_menu(), reply_markup=build_admin_menu())

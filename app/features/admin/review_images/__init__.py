from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import texts
from app.config import SIGNS_RU
from app.features.admin.dependencies import get_settings, is_admin
from app.features.admin.keyboards import ADMIN_REVIEW_IMAGE_CALLBACK, build_admin_menu, build_admin_signs_keyboard
from app.features.admin.states import AdminReviewImage
from app.features.admin.utils import detect_extension, review_destination_path, save_media
from app.services import media

router = Router()


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


@router.message(AdminReviewImage.file)
async def handle_admin_review_image_file(message: Message, state: FSMContext):
    if not is_admin(message.bot, message.from_user.id):
        await state.clear()
        await message.answer(texts.admin_forbidden())
        return
    extension = detect_extension(message)
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
    destination = review_destination_path(settings.media_dir, sign, extension)
    for ext in media.ALLOWED_EXTENSIONS:
        existing = destination.with_suffix(f".{ext}")
        if existing.exists():
            existing.unlink()
    success = await save_media(message, destination)
    if not success:
        await message.answer(texts.admin_save_failed())
        return
    await state.clear()
    await message.answer(texts.admin_review_image_saved(sign))
    await message.answer(texts.admin_menu(), reply_markup=build_admin_menu())

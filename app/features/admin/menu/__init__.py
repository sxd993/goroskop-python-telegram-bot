from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.features import texts
from app.features.menu_labels import ADMIN_PANEL_LABEL
from app.features.admin.dependencies import is_admin
from app.features.admin.keyboards import ADMIN_BACK_MENU_CALLBACK, build_admin_menu

router = Router()


@router.message(Command("admin"))
async def handle_admin_entry(message: Message, state: FSMContext):
    if not is_admin(message.bot, message.from_user.id):
        await state.clear()
        await message.answer(texts.admin_forbidden())
        return
    await state.clear()
    await message.answer(texts.admin_menu(), reply_markup=build_admin_menu())


@router.message(F.text.casefold() == ADMIN_PANEL_LABEL.casefold())
async def handle_admin_panel_button(message: Message, state: FSMContext):
    if not is_admin(message.bot, message.from_user.id):
        await state.clear()
        await message.answer(texts.admin_forbidden())
        return
    await state.clear()
    await message.answer(texts.admin_menu(), reply_markup=build_admin_menu())


@router.callback_query(F.data == ADMIN_BACK_MENU_CALLBACK)
async def handle_admin_back_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.bot, callback.from_user.id):
        await callback.answer(texts.admin_forbidden(), show_alert=True)
        return
    await state.clear()
    await callback.answer()
    await callback.message.answer(texts.admin_menu(), reply_markup=build_admin_menu())

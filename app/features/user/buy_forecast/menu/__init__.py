from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app import texts
from app.menu_labels import BUY_FORECAST_LABEL
from app.features.user.dependencies import ensure_user, get_db_path, get_settings, is_admin
from app.features.user.keyboards import build_layout_keyboard, build_start_keyboard
from app.services import media, state_machine
from app.services.state_machine import UserState

router = Router()


def build_user_start_markup(message: Message):
    user_id = message.from_user.id if message.from_user else None
    return build_start_keyboard(is_admin=is_admin(message.bot, user_id))


async def show_catalog_menu(message: Message, *, show_empty_message: bool = True) -> None:
    settings = get_settings(message.bot)
    year_years = media.available_yearly_years(settings.media_dir)
    month_years = media.available_monthly_years(settings.media_dir)
    if not year_years and not month_years:
        if show_empty_message:
            await message.answer(texts.no_content(), reply_markup=build_user_start_markup(message))
        return
    keyboard = build_layout_keyboard(has_year=bool(year_years), has_month=bool(month_years))
    await message.answer(texts.choose_forecast_kind(), reply_markup=keyboard)


@router.message(Command("start"))
async def handle_start(message: Message):
    await ensure_user(message.bot, message.from_user.id)
    db_path = get_db_path(message.bot)
    user_state = await state_machine.get_user_state(db_path, message.from_user.id)
    if user_state == UserState.REVIEW_PENDING:
        await state_machine.ensure_idle(db_path, message.from_user.id)
    await message.answer(texts.welcome(), reply_markup=build_user_start_markup(message))


@router.message(F.text.casefold() == BUY_FORECAST_LABEL.casefold())
async def handle_buy_forecast(message: Message):
    await ensure_user(message.bot, message.from_user.id)
    await show_catalog_menu(message, show_empty_message=True)



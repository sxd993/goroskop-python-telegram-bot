from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import MONTH_NAMES_RU, SIGNS_RU


ADMIN_ADD_FORECAST_CALLBACK = "admin:add_forecast"
ADMIN_DELETE_FORECAST_CALLBACK = "admin:delete_forecast"
ADMIN_STATS_CALLBACK = "admin:stats"
ADMIN_REVIEWS_CALLBACK = "admin:reviews"
ADMIN_BACK_MENU_CALLBACK = "admin-back:menu"


def build_admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить прогноз", callback_data=ADMIN_ADD_FORECAST_CALLBACK)
    builder.button(text="Удалить прогноз", callback_data=ADMIN_DELETE_FORECAST_CALLBACK)
    builder.button(text="Статистика продаж", callback_data=ADMIN_STATS_CALLBACK)
    builder.button(text="Отзывы", callback_data=ADMIN_REVIEWS_CALLBACK)
    builder.adjust(1)
    return builder.as_markup()


def build_admin_type_keyboard(include_back: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Годовой", callback_data="admin-type:year")
    builder.button(text="Месячный", callback_data="admin-type:month")
    builder.adjust(2)
    if include_back:
        builder.button(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)
        builder.adjust(2)
    return builder.as_markup()


def build_admin_years_keyboard(years: list[str], prefix: str, include_back: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for year in years:
        builder.button(text=year, callback_data=f"{prefix}:{year}")
    builder.adjust(3)
    if include_back:
        builder.button(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)
        builder.adjust(3)
    return builder.as_markup()


def build_admin_months_keyboard(months: list[int] | None = None, include_back: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    month_items = months or list(MONTH_NAMES_RU.keys())
    for month in month_items:
        name = MONTH_NAMES_RU.get(month, f"{month:02d}")
        builder.button(text=name, callback_data=f"admin-month:{month:02d}")
    builder.adjust(3)
    if include_back:
        builder.button(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)
        builder.adjust(3)
    return builder.as_markup()


def build_admin_signs_keyboard(signs: list[str] | None = None, include_back: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    sign_items = signs or list(SIGNS_RU.keys())
    for sign in sign_items:
        name = SIGNS_RU.get(sign, sign)
        builder.button(text=name, callback_data=f"admin-sign:{sign}")
    builder.adjust(3)
    if include_back:
        builder.button(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)
        builder.adjust(3)
    return builder.as_markup()


def build_admin_delete_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    # action example: "admin-del-confirm:yes" / "...:no"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Удалить", callback_data=f"{action}:yes")],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"{action}:no")],
        ]
    )

from pathlib import Path

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import SIGNS_RU
from app.menu_labels import (
    ADMIN_PANEL_LABEL,
    BUY_FORECAST_LABEL,
    REFERRAL_LABEL,
    SUPPORT_LABEL,
)
from app.services import media

REVIEW_CANCEL_CALLBACK = "review:cancel"
REVIEW_MENU_CALLBACK = "review:menu"

SIGN_EMOJI = {
    "aries": "♈",
    "taurus": "♉",
    "gemini": "♊",
    "cancer": "♋",
    "leo": "♌",
    "virgo": "♍",
    "libra": "♎",
    "scorpio": "♏",
    "sagittarius": "♐",
    "capricorn": "♑",
    "aquarius": "♒",
    "pisces": "♓",
}


def build_start_keyboard(*, is_admin: bool) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text=BUY_FORECAST_LABEL)],
        [KeyboardButton(text=REFERRAL_LABEL)],
        [KeyboardButton(text=SUPPORT_LABEL)],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text=ADMIN_PANEL_LABEL)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def build_layout_keyboard(*, has_year: bool, has_month: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_year:
        builder.button(text="📅 Годовой гороскоп", callback_data="mode:year")
    if has_month:
        builder.button(text="🗓️ Месячный гороскоп", callback_data="mode:month")
    builder.adjust(1)
    return builder.as_markup()


def build_years_keyboard(
    years, prefix: str, back: str | None = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for year in years:
        builder.button(text=f"📅 {year}", callback_data=f"{prefix}:{year}")
    builder.adjust(3)
    if back:
        builder.button(text="⬅️ Назад", callback_data=back)
        builder.adjust(3)
    return builder.as_markup()


def build_months_keyboard(
    media_dir: Path, year: str, back: str | None = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ym in media.months_for_year(media_dir, year):
        name = media.month_name_from_ym(ym)
        if name:
            builder.button(text=f"🗓️ {name}", callback_data=f"m-month:{ym}")
    builder.adjust(3)
    if back:
        builder.button(text="⬅️ Назад", callback_data=back)
        builder.adjust(3)
    return builder.as_markup()


def build_month_signs_keyboard(
    media_dir: Path, ym: str, back: str | None = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sign in media.available_month_signs(media_dir, ym):
        name = SIGNS_RU[sign]
        emoji = SIGN_EMOJI.get(sign, "🔮")
        builder.button(text=f"{emoji} {name}", callback_data=f"m-sign:{ym}:{sign}")
    builder.adjust(3)
    if back:
        builder.button(text="⬅️ Назад", callback_data=back)
        builder.adjust(3)
    return builder.as_markup()


def build_year_signs_keyboard(
    media_dir: Path, year: str, back: str | None = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sign in media.available_year_signs(media_dir, year):
        name = SIGNS_RU[sign]
        emoji = SIGN_EMOJI.get(sign, "🔮")
        builder.button(text=f"{emoji} {name}", callback_data=f"y-sign:{year}:{sign}")
    builder.adjust(3)
    if back:
        builder.button(text="⬅️ Назад", callback_data=back)
        builder.adjust(3)
    return builder.as_markup()


def build_pay_keyboard(
    product_id: str, back: str | None = None
) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay:{product_id}")]
    ]
    if back:
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_referral_prompt_keyboard(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"referral:yes:{order_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"referral:no:{order_id}"),
            ],
        ]
    )


def build_referral_skip_keyboard(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏭️ Пропустить", callback_data=f"referral:skip:{order_id}"),
            ],
        ]
    )


def build_review_keyboard(order_id: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="✍️ Оставить отзыв", callback_data=f"review:start:{order_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⏭️ Пропустить", callback_data=f"review:skip:{order_id}"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_review_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data=REVIEW_CANCEL_CALLBACK
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 В меню", callback_data=REVIEW_MENU_CALLBACK
                )
            ],
        ]
    )


def build_review_contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Поделиться номером", request_contact=True)],
            [KeyboardButton(text="⏭️ Пропустить")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def build_campaign_interest_keyboard(campaign_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔥 Мне интересно",
                    callback_data=f"campaign:interest:{campaign_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🙅‍♀️ Не интересно",
                    callback_data=f"campaign:decline:{campaign_id}",
                )
            ],
        ]
    )


def build_referral_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔗 Ссылка", callback_data="referral:link"),
                InlineKeyboardButton(text="🏷️ Код", callback_data="referral:code"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="referral:stats"),
            ],
        ]
    )



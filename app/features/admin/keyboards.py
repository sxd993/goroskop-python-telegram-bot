from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import MONTH_NAMES_RU, SIGNS_RU


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


ADMIN_ADD_FORECAST_CALLBACK = "admin:add_forecast"
ADMIN_DELETE_FORECAST_CALLBACK = "admin:delete_forecast"
ADMIN_STATS_CALLBACK = "admin:stats"
ADMIN_REVIEWS_CALLBACK = "admin:reviews"
ADMIN_REVIEW_IMAGE_CALLBACK = "admin:review_image"
ADMIN_BROADCASTS_CALLBACK = "admin:broadcasts"
ADMIN_BROADCAST_LIST_CALLBACK = "admin:broadcasts:list"
ADMIN_BROADCAST_ITEM_PREFIX = "admin:broadcasts:item"
ADMIN_BROADCAST_DELETE_PREFIX = "admin:broadcasts:delete"
ADMIN_BROADCAST_CREATE_CALLBACK = "admin:broadcasts:create"
ADMIN_BROADCAST_LAUNCH_PREFIX = "admin:broadcasts:launch"
ADMIN_BROADCAST_STATS_PREFIX = "admin:broadcasts:stats"
ADMIN_BROADCAST_BODY_PREFIX = "admin:broadcasts:body"
ADMIN_BROADCAST_RESPONSES_PREFIX = "admin:br:list"
ADMIN_BROADCAST_RESPONSES_ITEM_PREFIX = "admin:br:item"
ADMIN_BACK_MENU_CALLBACK = "admin-back:menu"
ADMIN_REVIEWS_PAGE_PREFIX = "admin-reviews:page"
ADMIN_REVIEWS_KIND_PREFIX = "admin-reviews:kind"
ADMIN_REVIEWS_FILTER_PAGE_PREFIX = "admin-reviews:pagef"
ADMIN_REVIEWS_MONTHS_PAGE_PREFIX = "admin-reviews:months-page"
ADMIN_REVIEWS_MONTH_OPEN_PREFIX = "admin-reviews:month-open"
ADMIN_REVIEW_OPEN_PREFIX = "ar:o"
ADMIN_STATS_KIND_PREFIX = "admin-stats:kind"
ADMIN_STATS_MONTHS_PAGE_PREFIX = "admin-stats:months-page"
ADMIN_STATS_MONTH_OPEN_PREFIX = "admin-stats:month-open"
ADMIN_STATS_YEARS_PAGE_PREFIX = "admin-stats:years-page"
ADMIN_STATS_YEAR_OPEN_PREFIX = "admin-stats:year-open"


def build_admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить прогноз", callback_data=ADMIN_ADD_FORECAST_CALLBACK)
    builder.button(text="🗑️ Удалить прогноз", callback_data=ADMIN_DELETE_FORECAST_CALLBACK)
    builder.button(text="📊 Статистика продаж", callback_data=ADMIN_STATS_CALLBACK)
    builder.button(text="💬 Отзывы", callback_data=ADMIN_REVIEWS_CALLBACK)
    builder.button(text="🖼️ Картинки после отзывов", callback_data=ADMIN_REVIEW_IMAGE_CALLBACK)
    builder.button(text="📢 Рассылки", callback_data=ADMIN_BROADCASTS_CALLBACK)
    builder.adjust(1)
    return builder.as_markup()


def build_admin_type_keyboard(include_back: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Годовой", callback_data="admin-type:year")
    builder.button(text="🗓️ Месячный", callback_data="admin-type:month")
    builder.adjust(2)
    if include_back:
        builder.button(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)
        builder.adjust(2)
    return builder.as_markup()


def build_admin_years_keyboard(years: list[str], prefix: str, include_back: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for year in years:
        builder.button(text=f"📅 {year}", callback_data=f"{prefix}:{year}")
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
        builder.button(text=f"🗓️ {name}", callback_data=f"admin-month:{month:02d}")
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
        emoji = SIGN_EMOJI.get(sign, "🔮")
        builder.button(text=f"{emoji} {name}", callback_data=f"admin-sign:{sign}")
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


def build_admin_reviews_list_keyboard(
    items: list[tuple[str, str]],
    *,
    prev_callback: str | None,
    next_callback: str | None,
    back_callback: str | None = None,
    include_back_to_menu: bool = True,
) -> InlineKeyboardMarkup:
    """
    items: list of (button_text, callback_data)
    """
    builder = InlineKeyboardBuilder()
    for text, callback_data in items:
        builder.button(text=text, callback_data=callback_data)
    builder.adjust(1)

    nav: list[InlineKeyboardButton] = []
    if prev_callback:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=prev_callback))
    if next_callback:
        nav.append(InlineKeyboardButton(text="➡️ Далее", callback_data=next_callback))
    if nav:
        builder.row(*nav)

    if back_callback:
        builder.row(InlineKeyboardButton(text="⬅️ К типам", callback_data=back_callback))

    if include_back_to_menu:
        builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK))

    return builder.as_markup()


def build_admin_review_detail_keyboard(*, back_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К списку", callback_data=back_callback)],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)],
        ]
    )


def build_admin_reviews_kind_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Годовые", callback_data=f"{ADMIN_REVIEWS_KIND_PREFIX}:year")
    builder.button(text="🗓️ Месячные", callback_data=f"{ADMIN_REVIEWS_KIND_PREFIX}:month")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK))
    return builder.as_markup()


def build_admin_reviews_months_keyboard(
    items: list[tuple[str, str]],
    *,
    page: int,
    prev_callback: str | None,
    next_callback: str | None,
    include_back_to_kinds: bool = True,
) -> InlineKeyboardMarkup:
    """
    items: list of (button_text, ym)
    """
    builder = InlineKeyboardBuilder()
    for text, ym in items:
        builder.button(text=text, callback_data=f"{ADMIN_REVIEWS_MONTH_OPEN_PREFIX}:{ym}:{page}")
    builder.adjust(1)

    nav: list[InlineKeyboardButton] = []
    if prev_callback:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=prev_callback))
    if next_callback:
        nav.append(InlineKeyboardButton(text="➡️ Далее", callback_data=next_callback))
    if nav:
        builder.row(*nav)

    if include_back_to_kinds:
        builder.row(InlineKeyboardButton(text="⬅️ К типам", callback_data=ADMIN_REVIEWS_CALLBACK))
    builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK))
    return builder.as_markup()


def build_admin_stats_kind_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Годовые", callback_data=f"{ADMIN_STATS_KIND_PREFIX}:year")
    builder.button(text="🗓️ Месячные", callback_data=f"{ADMIN_STATS_KIND_PREFIX}:month")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK))
    return builder.as_markup()


def build_admin_stats_months_keyboard(
    items: list[tuple[str, str]],
    *,
    page: int,
    has_prev: bool,
    has_next: bool,
    include_back_to_menu: bool = True,
) -> InlineKeyboardMarkup:
    """
    items: list of (button_text, ym)
    """
    builder = InlineKeyboardBuilder()
    for text, ym in items:
        builder.button(text=text, callback_data=f"{ADMIN_STATS_MONTH_OPEN_PREFIX}:{ym}:{page}")
    builder.adjust(1)

    nav: list[InlineKeyboardButton] = []
    if has_prev:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"{ADMIN_STATS_MONTHS_PAGE_PREFIX}:{page - 1}",
            )
        )
    if has_next:
        nav.append(
            InlineKeyboardButton(
                text="➡️ Далее",
                callback_data=f"{ADMIN_STATS_MONTHS_PAGE_PREFIX}:{page + 1}",
            )
        )
    if nav:
        builder.row(*nav)

    if include_back_to_menu:
        builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK))

    return builder.as_markup()


def build_admin_stats_years_keyboard(
    items: list[tuple[str, str]],
    *,
    page: int,
    has_prev: bool,
    has_next: bool,
    include_back_to_menu: bool = True,
) -> InlineKeyboardMarkup:
    """
    items: list of (button_text, year)
    """
    builder = InlineKeyboardBuilder()
    for text, year in items:
        builder.button(text=text, callback_data=f"{ADMIN_STATS_YEAR_OPEN_PREFIX}:{year}:{page}")
    builder.adjust(1)

    nav: list[InlineKeyboardButton] = []
    if has_prev:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"{ADMIN_STATS_YEARS_PAGE_PREFIX}:{page - 1}",
            )
        )
    if has_next:
        nav.append(
            InlineKeyboardButton(
                text="➡️ Далее",
                callback_data=f"{ADMIN_STATS_YEARS_PAGE_PREFIX}:{page + 1}",
            )
        )
    if nav:
        builder.row(*nav)

    if include_back_to_menu:
        builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK))

    return builder.as_markup()


def build_admin_stats_month_detail_keyboard(*, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К месяцам", callback_data=f"{ADMIN_STATS_MONTHS_PAGE_PREFIX}:{page}")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)],
        ]
    )


def build_admin_stats_year_detail_keyboard(*, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К годам", callback_data=f"{ADMIN_STATS_YEARS_PAGE_PREFIX}:{page}")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)],
        ]
    )


def build_broadcasts_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🆕 Создать рассылку", callback_data=ADMIN_BROADCAST_CREATE_CALLBACK)
    builder.button(text="📚 Список рассылок", callback_data=ADMIN_BROADCAST_LIST_CALLBACK)
    builder.button(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)
    builder.adjust(1)
    return builder.as_markup()


def build_broadcasts_list_keyboard(items: list[tuple[str, str]], prefix: str, *, include_back: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, campaign_id in items:
        builder.button(text=text, callback_data=f"{prefix}:{campaign_id}")
    builder.adjust(1)
    if include_back:
        builder.button(text="⬅️ Назад", callback_data=ADMIN_BROADCASTS_CALLBACK)
        builder.adjust(1)
    return builder.as_markup()


def build_broadcast_responses_list_keyboard(
    campaign_id: str,
    campaign_token: str,
    responses: list[dict],
    *,
    page: int,
    has_next: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for resp in responses:
        label = resp.get("full_name")
        if not label:
            label = f"User {resp['user_id']}"
        resp_token = resp.get("_token", resp["id"])
        builder.button(
            text=label,
            callback_data=f"{ADMIN_BROADCAST_RESPONSES_ITEM_PREFIX}:{campaign_token}:{page}:{resp_token}",
        )
    builder.adjust(1)

    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"{ADMIN_BROADCAST_RESPONSES_PREFIX}:{campaign_token}:{page - 1}",
            )
        )
    if has_next:
        nav.append(
            InlineKeyboardButton(
                text="➡️ Далее",
                callback_data=f"{ADMIN_BROADCAST_RESPONSES_PREFIX}:{campaign_token}:{page + 1}",
            )
        )
    if nav:
        builder.row(*nav)

    builder.row(
        InlineKeyboardButton(
            text="⬅️ К рассылке",
            callback_data=f"{ADMIN_BROADCAST_ITEM_PREFIX}:{campaign_id}",
        ),
        InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK),
    )
    return builder.as_markup()


def build_broadcast_response_detail_keyboard(
    *,
    campaign_id: str,
    campaign_token: str,
    page: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К списку",
                    callback_data=f"{ADMIN_BROADCAST_RESPONSES_PREFIX}:{campaign_token}:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К рассылке",
                    callback_data=f"{ADMIN_BROADCAST_ITEM_PREFIX}:{campaign_id}",
                )
            ],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)],
        ]
    )


def build_broadcast_stats_keyboard(campaign_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К рассылке",
                    callback_data=f"{ADMIN_BROADCAST_ITEM_PREFIX}:{campaign_id}",
                )
            ],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)],
        ]
    )


def build_broadcast_body_keyboard(campaign_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К рассылке",
                    callback_data=f"{ADMIN_BROADCAST_ITEM_PREFIX}:{campaign_id}",
                )
            ],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)],
        ]
    )


def build_broadcast_item_menu_keyboard(campaign_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Запустить", callback_data=f"{ADMIN_BROADCAST_LAUNCH_PREFIX}:{campaign_id}")
    builder.button(text="👁️ Текст рассылки", callback_data=f"{ADMIN_BROADCAST_BODY_PREFIX}:{campaign_id}")
    builder.button(text="📈 Статистика", callback_data=f"{ADMIN_BROADCAST_STATS_PREFIX}:{campaign_id}")
    builder.button(text="🗑️ Удалить рассылку", callback_data=f"{ADMIN_BROADCAST_DELETE_PREFIX}:{campaign_id}")
    builder.button(text="⬅️ К списку", callback_data=ADMIN_BROADCAST_LIST_CALLBACK)
    builder.button(text="⬅️ В меню", callback_data=ADMIN_BACK_MENU_CALLBACK)
    builder.adjust(1)
    return builder.as_markup()

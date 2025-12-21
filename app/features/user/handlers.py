from aiogram import Router

from app.config import Settings

from .dependencies import setup_user_settings
from .buy_forecast.menu import handle_buy_forecast, handle_start, show_catalog_menu, router as menu_router
from .buy_forecast.navigation import router as navigation_router
from .buy_forecast.payments import router as payments_router
from .buy_forecast.campaigns import router as campaigns_router
from .buy_forecast.reviews import handle_review_text, router as reviews_router
from .support import handle_support, router as support_router

router = Router()
router.include_router(menu_router)
router.include_router(support_router)
router.include_router(navigation_router)
router.include_router(payments_router)
router.include_router(campaigns_router)
router.include_router(reviews_router)


def setup_handlers(settings: Settings) -> None:
    setup_user_settings(settings)


# Re-export routers/handlers for compatibility
__all__ = [
    "router",
    "setup_handlers",
    "handle_start",
    "handle_review_text",
    "handle_buy_forecast",
    "handle_support",
    "show_catalog_menu",
    "menu_router",
    "navigation_router",
    "payments_router",
    "reviews_router",
    "support_router",
]

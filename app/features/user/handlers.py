from aiogram import Router

from app.config import Settings

from .dependencies import setup_user_settings
from .menu import handle_buy_forecast, handle_start, handle_support, show_catalog_menu, router as menu_router
from .navigation import router as navigation_router
from .payments import router as payments_router
from .reviews import handle_review_text, router as reviews_router
from .campaigns import router as campaigns_router

router = Router()
router.include_router(menu_router)
router.include_router(navigation_router)
router.include_router(payments_router)
router.include_router(reviews_router)
router.include_router(campaigns_router)


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
]

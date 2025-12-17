from aiogram import Router

from app.config import Settings

from .dependencies import setup_admin_settings
from .forecasts import router as forecasts_router
from .menu import router as menu_router
from .reviews import router as reviews_router
from .reviews.images import router as review_images_router
from .stats import router as stats_router

router = Router()
router.include_router(menu_router)
router.include_router(forecasts_router)
router.include_router(stats_router)
router.include_router(reviews_router)
router.include_router(review_images_router)


def setup_handlers(settings: Settings) -> None:
    setup_admin_settings(settings)


__all__ = [
    "router",
    "setup_handlers",
]

from aiogram import Router

from app.config import Settings

from .dependencies import setup_admin_settings
from .bulk_mail import router as broadcasts_router
from .add_forecast import router as add_forecast_router
from .delete_forecast import router as delete_forecast_router
from app.features.user.admin_panel import router as menu_router
from .reviews import router as reviews_router
from .review_images import router as review_images_router
from .stats import router as stats_router

router = Router()
router.include_router(menu_router)
router.include_router(add_forecast_router)
router.include_router(delete_forecast_router)
router.include_router(stats_router)
router.include_router(reviews_router)
router.include_router(review_images_router)
router.include_router(broadcasts_router)


def setup_handlers(settings: Settings) -> None:
    setup_admin_settings(settings)


__all__ = [
    "router",
    "setup_handlers",
]

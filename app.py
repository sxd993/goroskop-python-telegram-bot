import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from app.config import load_settings
from app.features.admin.handlers import router as admin_router, setup_handlers as setup_admin_handlers
from app.features.user.handlers import router as navigation_router, setup_handlers
from app.services.db import init_db


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    await init_db(settings.db_path)

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    setup_handlers(settings)
    setup_admin_handlers(settings)

    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(navigation_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

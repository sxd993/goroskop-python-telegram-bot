import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

import handlers
from config import load_settings
from db import init_db


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    await init_db(settings.db_path)

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    handlers.setup(settings)

    dp = Dispatcher()
    dp.include_router(handlers.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

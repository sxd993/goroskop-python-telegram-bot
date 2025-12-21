from aiogram import F, Router
from aiogram.types import Message

from app import texts
from app.menu_labels import SUPPORT_LABEL
from app.features.user.buy_forecast.menu import build_user_start_markup

router = Router()

SUPPORT_URL = "https://t.me/alexandekipa"


@router.message(F.text.casefold() == SUPPORT_LABEL.casefold())
async def handle_support(message: Message):
    await message.answer(texts.support_contact(SUPPORT_URL), reply_markup=build_user_start_markup(message))

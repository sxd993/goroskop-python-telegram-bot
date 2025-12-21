from aiogram.fsm.state import State, StatesGroup


class CampaignResponseFlow(StatesGroup):
    fio = State()
    birthdate = State()
    contact = State()

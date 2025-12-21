from aiogram.fsm.state import State, StatesGroup


class AdminUpload(StatesGroup):
    kind = State()
    year = State()
    month = State()
    sign = State()
    file = State()


class AdminDelete(StatesGroup):
    kind = State()
    year = State()
    month = State()
    sign = State()
    confirm = State()


class AdminReviewImage(StatesGroup):
    sign = State()
    file = State()


class AdminBroadcastCreate(StatesGroup):
    title = State()
    body = State()
    price = State()

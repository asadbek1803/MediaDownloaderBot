from aiogram.filters.state import StatesGroup, State


class Test(StatesGroup):
    Q1 = State()
    Q2 = State()


class AdminState(StatesGroup):
    are_you_sure = State()
    ask_ad_content = State()

class AdminStates(StatesGroup):
    add_channel = State()
    del_channel = State()
    add_admin = State()
    del_admin = State()
    ban_user = State()

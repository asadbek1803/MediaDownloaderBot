from aiogram.fsm.state import State, StatesGroup

class SelectLang(StatesGroup):
    choose = State()  # Tilni tanlash bosqichi

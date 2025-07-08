from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loader import bot
from app import logger
from states.select_lang import SelectLang
from utils.db.postgres import get_user
from keyboards.reply.language import language_keyboard
from utils.lang import lang

router = Router()

@router.message(Command("language"))
async def change_language(message: types.Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user and user.is_banned:
        await message.answer_sticker("CAACAgEAAxkBAAEO3zhoa69Gw_uAcW9OY_RKWBf3fT18zAAC_gIAAoEiIEQJoqI2DvPFOzYE")
        await message.answer("🚫 Siz banlangansiz. Botdan foydalanish mumkin emas.")
        return

    await state.set_state(SelectLang.choose)
    await message.answer("🌐 Qaysi tilni tanlaysiz?", reply_markup=language_keyboard())

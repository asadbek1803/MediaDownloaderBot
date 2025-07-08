from aiogram import Router, types
from aiogram.filters import Command
from utils.db.postgres import get_user
from utils.lang import lang

router = Router()

@router.message(Command("help"))
async def bot_help(message: types.Message):
    user = await get_user(message.from_user.id)
    user_lang = user.lang if user and user.lang in lang else "uz"
    message.answer_sticker("CAACAgEAAxkBAAEO3zxoa6_v5Nd-xTZP1vIVXwABupVbp9oAAqQBAAKMQrBFweNnmEiTT6o2BA")
    await message.answer(lang[user_lang]["help"], parse_mode="HTML")

@router.message(Command("dev"))
async def dev_info(message: types.Message):
    text = (
        "<b>👨‍💻 Dasturchi bilan bog‘lanish:</b>\n\n"
        "📍 Telegram: <a href='https://t.me/asadbek_074'>@asadbek_074</a>\n"
        "📸 Instagram: <a href='https://instagram.com/as1dbek_'>@as1dbek_</a>\n\n"
        "📬 Taklif yoki savollaringiz bo‘lsa bemalol yozing!"
    )

    await message.answer_sticker("CAACAgEAAxkBAAEO3zxoa6_v5Nd-xTZP1vIVXwABupVbp9oAAqQBAAKMQrBFweNnmEiTT6o2BA")
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
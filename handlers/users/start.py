from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from loader import bot
from app import logger
from utils.lang import lang
from utils.db.postgres import get_user, add_user, get_all_admins
from states.select_lang import SelectLang
from keyboards.reply.language import language_keyboard
from middlewares.azolikni_tekshir import CallbackQuery, handle_subscription_check

router = Router()

@router.callback_query(lambda c: c.data == "check_subscription")
async def process_subscription_check(callback: CallbackQuery):
    await handle_subscription_check(callback, bot)

@router.message(CommandStart())
async def do_start(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username or "unknown"

    user = await get_user(telegram_id)

    # 1. Foydalanuvchi bazada mavjud emasmi? Unda til tanlatsin.
    if not user:
        await state.set_state(SelectLang.choose)
        await message.answer_sticker("CAACAgEAAxkBAAEO3zZoa67JyrFzzGMCOTc-4sbU0VjnBAACMQIAAsOjKEdLBVdiYsQQXzYE")
        await message.answer("🌐 Iltimos, tilni tanlang:", reply_markup=language_keyboard())
        return

    # 2. Agar banlangan bo‘lsa — chiqmasin
    if user.is_banned:
        await message.answer_sticker("CAACAgEAAxkBAAEO3zhoa69Gw_uAcW9OY_RKWBf3fT18zAAC_gIAAoEiIEQJoqI2DvPFOzYE")
        await message.answer(lang[user.lang]['banned'])
        return

    # 3. Aks holda start xabarini chiqarish
    await message.answer_sticker("CAACAgEAAxkBAAEO3y5oa65yaBgwDjJW3f956AibLKXEXAACpQIAAkb-8Ec467BfJxQ8djYE")
    await message.answer(lang[user.lang]['start'], parse_mode="HTML")


@router.message(SelectLang.choose)
async def process_language_choice(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username or "unknown"

    lang_code = "uz"
    if "Русский" in message.text:
        lang_code = "ru"
    elif "English" in message.text:
        lang_code = "en"

    user = await get_user(telegram_id)

    if user:
        user.lang = lang_code
        await user.save()
        await message.answer_sticker("CAACAgEAAxkBAAEO3zpoa6-XPrqhnNv3nVtCbOCKbPwcZgACnwMAAonfWETOikC8ytx7RTYE")
        await message.answer("✅ Til muvaffaqiyatli o‘zgartirildi!", reply_markup=types.ReplyKeyboardRemove())
        await message.answer(lang[lang_code]["start"], parse_mode="HTML")
    else:
        # Yangi user — bazaga yozib qo‘yamiz
        from utils.db.postgres import add_user, get_all_admins
        await add_user(full_name, telegram_id, username)
        user = await get_user(telegram_id)
        user.lang = lang_code
        await user.save()

        # Adminlarga xabar
        admins = await get_all_admins()
        msg = lang[lang_code]['new_user_admin_notice'].format(
            full_name=full_name,
            username=username,
            telegram_id=telegram_id
        )
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, msg, parse_mode="HTML")
            except Exception as err:
                logger.warning(f"Admin xabar yuborilmadi: {err}")
        await message.answer_sticker("CAACAgEAAxkBAAEO3zpoa6-XPrqhnNv3nVtCbOCKbPwcZgACnwMAAonfWETOikC8ytx7RTYE")
        await message.answer("✅ Til tanlandi. Botdan foydalanishingiz mumkin.")
        await message.answer(lang[lang_code]["start"], parse_mode="HTML")

    await state.clear()


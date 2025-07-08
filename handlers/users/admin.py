import logging
import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

from loader import bot
from keyboards.inline.buttons import are_you_sure_markup
from states.test import AdminState, AdminStates
from filters.admin import IsBotAdminFilter
from utils.db.postgres import (
    get_all_admins, select_all_users, select_all_user_ids, delete_all_users,
    add_channel, delete_channel, get_all_channels,
    get_user, select_all_users
    )
from utils.pgtoexcel import export_to_excel

router = Router()

# 📌 bot ishga tushganda admin ro'yxatini cache qilamiz


# users_for_advertisement = await select_all_user_ids()  # <-- bu ham await ishlatilgan bo'lishi kerak


# 🔹 1. Barcha foydalanuvchilar ro'yxatini Excelga eksport qilish

@router.message(Command('admin'))
async def admin_panel(message: types.Message):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    text = (
        "👮‍♂️ Admin panelga xush kelibsiz!\n\n"
        "Quyidagi buyruqlarni bajarishingiz mumkin:\n"
        "/allusers - Barcha foydalanuvchilar ro'yxatini Excelga eksport qilish\n"
        "/reklama - Reklama postini yuborish\n"
        "/cleandb - Baza ma'lumotlarini tozalash"
        "/addchannel - Kanal qo‘shish\n"
        "/delchannel - Kanal o‘chirish\n"
        "/addadmin - Admin qo‘shish\n"
        "/deladmin - Admin o‘chirish\n"
        "/pausebot - Botni pauza qilish\n"
        "/stat - Statistika ko‘rish\n"
        "/ban - Foydalanuvchini ban qilish"
    )
    await message.answer(text)


@router.message(Command('allusers'))
async def get_all_users(message: types.Message):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return

    users = await select_all_users()
    
    file_path = "data/users_list.xlsx"
    await export_to_excel(
        data=users,
        headings=['ID', 'Full Name', 'Username', 'Telegram ID', 'Is Admin', 'Is Banned', 'Created At'],
        filepath=file_path
    )

    await message.answer_document(FSInputFile(file_path))


# 🔹 2. Admindan reklama postini so'rash
@router.message(Command('reklama'))
async def ask_ad_content(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas"
                             )
        return
    await message.answer("📢 Reklama uchun postni yuboring:")
    await state.set_state(AdminState.ask_ad_content)


# 🔹 3. Reklamani barcha foydalanuvchilarga yuborish
@router.message(AdminState.ask_ad_content)
async def send_ad_to_users(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    users_for_advertisement = await select_all_user_ids() 
    count = 0

    for user_id in users_for_advertisement:
        try:
            await message.send_copy(chat_id=user_id)
            count += 1
            await asyncio.sleep(0.05)  # antispam delay
        except Exception as error:
            logging.info(f"🚫 Reklama yuborilmadi: {user_id}. Xatolik: {error}")

    await message.answer(f"✅ Reklama {count} ta foydalanuvchiga yuborildi.")
    await state.clear()


# 🔹 4. Bazani tozalashdan oldin tasdiqlash
@router.message(Command('cleandb'))
async def ask_are_you_sure(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    msg = await message.reply(
        "⚠️ Haqiqatdan ham bazani tozalamoqchimisiz?",
        reply_markup=are_you_sure_markup
    )
    await state.update_data(msg_id=msg.message_id)
    await state.set_state(AdminState.are_you_sure)


# 🔹 5. Callback orqali bazani tozalashni tasdiqlash yoki rad etish
@router.callback_query(AdminState.are_you_sure)
async def clean_db(call: types.CallbackQuery, state: FSMContext):
    if call.message.from_user.id not in await get_all_admins():
        await call.message.answer("⚠️ Sizga kirish mumkin emas")
        return
    data = await state.get_data()
    msg_id = data.get('msg_id')

    if call.data == 'yes':
        await delete_all_users()
        text = "✅ Ma'lumotlar bazasi tozalandi."
    elif call.data == 'no':
        text = "❌ Amal bekor qilindi."

    await bot.edit_message_text(
        text=text,
        chat_id=call.message.chat.id,
        message_id=msg_id
    )
    await state.clear()



# 🔹 Kanal qo‘shish
@router.message(Command('addchannel'))
async def add_channel_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    await message.answer("➕ Kanal username va ID sini quyidagicha yuboring:\n\n`@kanal_username | kanal_id`")
    await state.set_state(AdminStates.add_channel)

@router.message(AdminStates.add_channel)
async def save_channel(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    try:
        text = message.text
        username, channel_id = text.split("|")
        username = username.strip()
        channel_id = int(channel_id.strip())
        await add_channel(username, channel_id)
        await message.answer(f"✅ Kanal qo‘shildi: {username}")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")
    await state.clear()

# 🔹 Kanal o‘chirish
@router.message(Command('delchannel'))
async def delete_channel_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    await message.answer("➖ O‘chirish uchun kanal ID sini yuboring:")
    await state.set_state(AdminStates.del_channel)

@router.message(AdminStates.del_channel)
async def delete_channel_action(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    try:
        channel_id = int(message.text)
        await delete_channel(channel_id)
        await message.answer(f"✅ Kanal o‘chirildi.")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")
    await state.clear()

# 🔹 Admin qo‘shish
from utils.db.postgres import get_user

@router.message(Command('addadmin'))
async def add_admin_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return 
    await message.answer("➕ Admin qilmoqchi bo‘lgan foydalanuvchi ID sini yuboring:")
    await state.set_state(AdminStates.add_admin)

@router.message(AdminStates.add_admin)
async def add_admin_action(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    telegram_id = int(message.text)
    user = await get_user(telegram_id)
    if user:
        user.is_admin = True
        await user.save()
        await message.answer("✅ Admin qo‘shildi.")
       
    else:
        await message.answer("❌ Bunday foydalanuvchi topilmadi.")
    await state.clear()

# 🔹 Admin o‘chirish
@router.message(Command('deladmin'))
async def del_admin_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    await message.answer("➖ Adminlikdan olib tashlamoqchi bo‘lgan foydalanuvchi ID sini yuboring:")
    await state.set_state(AdminStates.del_admin)

@router.message(AdminStates.del_admin)
async def del_admin_action(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    telegram_id = int(message.text)
    user = await get_user(telegram_id)
    if user and user.is_admin:
        user.is_admin = False
        await user.save()
        await message.answer("✅ Adminlikdan olib tashlandi.")
       
    else:
        await message.answer("❌ Bunday admin topilmadi.")
    await state.clear()

# 🔹 Botni pauza qilish
PAUSE = False

@router.message(Command('pausebot'))
async def pause_bot(message: types.Message):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    global PAUSE
    PAUSE = not PAUSE
    holat = "⏸ Pauzada" if PAUSE else "▶️ Aktiv"
    await message.answer(f"Bot holati: {holat}")

# 🔹 Statistika
@router.message(Command('stat'))
async def show_stats(message: types.Message):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    from utils.db.postgres import select_all_users
    users = await select_all_users()
    total = len(users)
    banned = len([u for u in users if u[5]])  # is_banned 5-chi index
    await message.answer(f"📊 Statistika:\n\nJami foydalanuvchilar: {total}\nBlok qilganlar: {banned}")

# 🔹 Foydalanuvchini ban qilish
@router.message(Command('ban'))
async def ban_user_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    await message.answer("🚫 Ban qilmoqchi bo‘lgan foydalanuvchi ID sini yuboring:")
    await state.set_state(AdminStates.ban_user)

@router.message(AdminStates.ban_user)
async def ban_user_action(message: types.Message, state: FSMContext):
    if message.from_user.id not in await get_all_admins():
        await message.answer("⚠️ Sizga kirish mumkin emas")
        return
    telegram_id = int(message.text)
    user = await get_user(telegram_id)
    if user:
        user.is_banned = True
        await user.save()
        await message.answer("✅ Foydalanuvchi ban qilindi.")
    else:
        await message.answer("❌ Bunday foydalanuvchi topilmadi.")
    await state.clear()

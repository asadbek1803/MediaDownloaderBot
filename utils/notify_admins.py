import logging
import platform
from datetime import datetime
from aiogram import Bot
from .db.postgres import get_all_admins, User


# HTML belgilaridan foydalanish uchun aiogramda parse_mode=HTML ishlatamiz
async def on_startup_notify(bot: Bot):
    try:
        bot_info = await bot.me()
        total_users = await User.all().count()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_info = platform.uname()

        message = (
            "<b>🚀 Bot ishga tushdi!</b>\n\n"
            f"<b>🆔 Bot ID:</b> <code>{bot_info.id}</code>\n"
            f"<b>🔗 Username:</b> @{bot_info.username}\n"
            f"<b>👥 Foydalanuvchilar soni:</b> {total_users}\n"
            f"<b>🕒 Ishga tushgan vaqti:</b> {current_time}\n\n"
            f"<b>🖥 Tizim:</b> {system_info.system} {system_info.release}\n"
            f"<b>💾 Hostname:</b> {system_info.node}\n"
            f"<b>🧠 Processor:</b> {system_info.processor}"
        )

        for admin_id in await get_all_admins():
            try:
                await bot.send_message(chat_id=int(admin_id), text=message, parse_mode="HTML")
            except Exception as err:
                logging.exception(f"❌ Xatolik yuborishda: {admin_id} -> {err}")

    except Exception as e:
        logging.exception(f"❌ on_startup_notify funksiyasida umumiy xatolik: {e}")
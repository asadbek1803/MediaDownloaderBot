from aiogram import Bot
from aiogram.methods.set_my_commands import BotCommand
from aiogram.types import BotCommandScopeAllPrivateChats


async def set_default_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="⚡ Botni ishga tushirish"),
        BotCommand(command="/help", description="❓ Yordam"),
        BotCommand(command="/language", description="⚙️ Tilni o'zgartirish"),
        BotCommand(command="/download", description="📸 Videoni yuklab olish"),
        BotCommand(command="/limit", description="📊 Mening limitim"),
        BotCommand(command="/audio", description="🔉 Youtube MP3 yuklash"),
        BotCommand(command="/dev", description="👨‍💻 Dasturchi")


    ]
    await bot.set_my_commands(commands=commands, scope=BotCommandScopeAllPrivateChats())

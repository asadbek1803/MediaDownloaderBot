import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.middlewares.request_logging import logger
from aiogram.enums import ChatType



def setup_handlers(dispatcher: Dispatcher) -> None:
    """HANDLERS"""
    from handlers import setup_routers

    dispatcher.include_router(setup_routers())


def setup_middlewares(dispatcher: Dispatcher, bot: Bot) -> None:
    """MIDDLEWARE"""
    from middlewares.throttling import ThrottlingMiddleware
    from middlewares.azolikni_tekshir import ChannelMembershipMiddleware
    #router.middleware(ChannelMembershipMiddleware(bot=bot, skip_admins=True))
    # Spamdan himoya qilish uchun klassik ichki o'rta dastur. So'rovlar orasidagi asosiy vaqtlar 0,5 soniya
    dispatcher.message.middleware(ThrottlingMiddleware(slow_mode_delay=0.5))
    dispatcher.message.middleware(ChannelMembershipMiddleware(bot=bot, skip_admins=True))


def setup_filters(dispatcher: Dispatcher) -> None:
    """FILTERS"""
    from filters import ChatTypeFilter

    # Chat turini aniqlash uchun klassik umumiy filtr
    # Filtrni handlers/users/__init__ -dagi har bir routerga alohida o'rnatish mumkin
    dispatcher.message.filter(ChatTypeFilter(chat_types=[ChatType.PRIVATE]))



async def setup_aiogram(dispatcher: Dispatcher, bot: Bot) -> None:
    logger.info("Configuring aiogram")
    setup_handlers(dispatcher=dispatcher)
    setup_middlewares(dispatcher=dispatcher, bot=bot)
    setup_filters(dispatcher=dispatcher)
    logger.info("Configured aiogram")

async def database_connected():
    from tortoise import Tortoise
    from data.config import DB_URL
    logger.info("Connecting to the database Tortoise-ORM")
    await Tortoise.init(
        db_url=DB_URL,
        modules={"models": ["utils.db.models"]}  # bu yerda model faylingiz
    )
    await Tortoise.generate_schemas()

async def aiogram_on_startup_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    from utils.set_bot_commands import set_default_commands
    from utils.notify_admins import on_startup_notify
    from handlers.users.download_media import start_queue_processing

    logger.info("Database connected")
    await database_connected()

    logger.info("Starting polling")
    await bot.delete_webhook(drop_pending_updates=True)
    await setup_aiogram(bot=bot, dispatcher=dispatcher)
    await on_startup_notify(bot=bot)
    await set_default_commands(bot=bot)
    logger.info("Kutish rejimi ishlamoqda")
    await start_queue_processing()



async def aiogram_on_shutdown_polling(dispatcher: Dispatcher, bot: Bot):
    logger.info("Stopping polling")
    await bot.session.close()
    await dispatcher.storage.close()


def main():
    """CONFIG"""
    from data.config import BOT_TOKEN
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.fsm.storage.memory import MemoryStorage

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dispatcher = Dispatcher(storage=storage)

    dispatcher.startup.register(aiogram_on_startup_polling)
    dispatcher.shutdown.register(aiogram_on_shutdown_polling)
    asyncio.run(dispatcher.start_polling(bot, close_bot_session=True))
    # allowed_updates=['message', 'chat_member']


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped!")

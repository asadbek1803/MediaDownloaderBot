from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.utils.i18n import I18n, FSMI18nMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from data.config import BOT_TOKEN



bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


storage = MemoryStorage()
dispatcher = Dispatcher(storage=storage)



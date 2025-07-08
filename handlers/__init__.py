from aiogram import Router
from aiogram.enums import ChatType

from filters import ChatTypeFilter


def setup_routers() -> Router:
    from .users import admin, start, help, select_language, download_media, youtube, instagram, tiktok
    from .errors import error_handler

    router = Router()

    # Agar kerak bo'lsa, o'z filteringizni o'rnating
    start.router.message.filter(ChatTypeFilter(chat_types=[ChatType.PRIVATE]))

    router.include_routers(admin.router, start.router, download_media.router, select_language.router, help.router, error_handler.router)

    return router

import os
from tortoise import Tortoise
from .models import User, Channels

DB_URL = os.getenv('DB_URL', 'DB bo\'lishi shart')

async def init():
    await Tortoise.init(
        db_url=DB_URL,
        modules={'models': ['__main__']}

    )
    await Tortoise.generate_schemas()


async def add_admin(telegram_id: int) -> bool:
    try:
        user = User.get_or_none(telegram_id=telegram_id)
        user.is_admin = True
        return True
    except Exception as e:
        return False

async def delete_admin(telegram_id: int) -> bool:
    try:
        user = User.get_or_none(telegram_id=telegram_id)
        user.is_admin = False
        return True
    except Exception as e:
        return False

# Database functions
async def get_all_channels():
    """
    Barcha kanallar ro'yxatini olish
    """
    return await Channels.all()

async def add_channel(channel_username: str, channel_id: int):
    """
    Yangi kanal qo'shish
    """
    return await Channels.create(
        channel_username=channel_username,
        channel_id=channel_id
    )

async def delete_channel(channel_id: int):
    """
    Kanalni o'chirish
    """
    return await Channels.filter(channel_id=channel_id).delete()


# Foydalanuvchi qo'shish
async def add_user(full_name: str, telegram_id: int, username: str):
    return await User.create(
        full_name=full_name,
        telegram_id=telegram_id,
        username=username,
        is_banned=False  # default qiymat berib qo‘yamiz
    )


async def get_user(telegram_id: int):
    return await User.get_or_none(telegram_id=telegram_id)


# Barcha foydalanuvchilarni olish
async def select_all_users():
    """
    Barcha foydalanuvchilarni olish
    """
    return await User.all().values_list('id', 'full_name', 'username', 'telegram_id', 'is_admin', 'is_banned', 'created_at')


async def select_all_user_ids():
    """
    Telegramga yuborish uchun faqat foydalanuvchilarning telegram_id ro‘yxati
    """
    return await User.filter(is_banned=False).values_list('telegram_id', flat=True)


async def check_user_access(telegram_id: int, full_name: str, username: str) -> bool:
    user = await get_user(telegram_id)

    if not user:
        # Agar mavjud bo‘lmasa — yaratamiz
        await add_user(full_name, telegram_id, username)
        return True

    if user.is_banned:
        # Banlangan foydalanuvchi
        return False

    return True  # Ruxsat berilgan foydalanuvchi

async def delete_all_users():
    """
    Barcha foydalanuvchilarni o'chirish
    """
    await User.all().delete()


async def get_all_admins():
    """
    Barcha adminlarni olish
    """
    return await User.filter(is_admin=True).all().values_list('telegram_id', flat=True)


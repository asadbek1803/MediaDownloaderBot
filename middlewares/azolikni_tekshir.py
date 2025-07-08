from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram import Bot
from utils.db.postgres import get_all_channels, get_all_admins
from typing import Callable, Dict, Any, Awaitable, Union
import logging


# Middleware
class ChannelMembershipMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot, skip_admins: bool = True):
        self.bot = bot
        self.skip_admins = skip_admins
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        
        # Agar CallbackQuery bo'lsa, message ni olish
        if isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            message = event.message
        else:
            user_id = event.from_user.id
            message = event

        # Adminlarni tekshirish (agar skip_admins True bo'lsa)
        if self.skip_admins:
            try:
                # Bu yerda siz o'zingizning admin tekshirish funksiyangizni chaqirishingiz mumkin
                # Masalan: is_admin = await check_if_admin(user_id)
                # Hozircha oddiy admin ID'larni tekshiramiz
                 # Bu yerga o'zingizning admin ID'laringizni qo'ying
                if user_id in await get_all_admins():
                    return await handler(event, data)
            except Exception as e:
                logging.error(f"Admin tekshirishda xatolik: {e}")

        # Barcha majburiy kanallarni olish
        channels = await get_all_channels()
        
        if not channels:
            # Agar majburiy kanallar mavjud bo'lmasa, oddiy davom etish
            return await handler(event, data)

        not_subscribed_channels = []
        
        for channel in channels:
            try:
                # Foydalanuvchining kanal a'zoligini tekshirish
                member = await self.bot.get_chat_member(
                    chat_id=channel.channel_id,
                    user_id=user_id
                )
                
                # Agar foydalanuvchi a'zo bo'lmasa yoki chiqib ketgan bo'lsa
                if member.status in ['left', 'kicked']:
                    not_subscribed_channels.append(channel)
                    
            except TelegramBadRequest as e:
                # Agar bot kanalga qo'shilmagan bo'lsa yoki boshqa xatolik bo'lsa
                logging.error(f"Kanal {channel.channel_username} tekshirishda xatolik: {e}")
                continue
            except Exception as e:
                logging.error(f"Kutilmagan xatolik: {e}")
                continue

        # Agar foydalanuvchi barcha kanallarga a'zo bo'lsa
        if not not_subscribed_channels:
            return await handler(event, data)

        # Agar a'zo bo'lmagan kanallar mavjud bo'lsa, xabar yuborish
        await self.send_subscription_message(message, not_subscribed_channels)
        return  # Handler'ni chaqirmaslik

    async def send_subscription_message(self, message: Message, channels: list):
        """
        A'zo bo'lmagan kanallar haqida xabar yuborish
        """
        text = "🔒 <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'lishingiz kerak:</b>\n\n"
        
        # Inline tugmalar yaratish
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        for channel in channels:
            # Kanal username mavjud bo'lsa
            if channel.channel_username:
                # @ belgisini tekshirish va qo'shish
                username = channel.channel_username
                if not username.startswith('@'):
                    username = f"@{username}"
                
                text += f"📢 <b>{username}</b>\n"
                
                # Inline tugma qo'shish
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=f"📢 {username}",
                        url=f"https://t.me/{username.replace('@', '')}"
                    )
                ])
            else:
                text += f"📢 Kanal ID: {channel.channel_id}\n"
        
        # Tekshirish tugmasi
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="✅ A'zolikni tekshirish",
                callback_data="check_subscription"
            )
        ])
        
        text += "\n💡 <b>A'zo bo'lgandan so'ng \"A'zolikni tekshirish\" tugmasini bosing!</b>"
        
        try:
            await message.answer(
                text, 
                parse_mode="HTML", 
                disable_web_page_preview=True,
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Xabar yuborishda xatolik: {e}")
            # Oddiy matn ko'rinishida yuborish
            simple_text = "🔒 Botdan foydalanish uchun majburiy kanallarga a'zo bo'lishingiz kerak!"
            await message.answer(simple_text)

# Yordamchi funksiyalar
async def check_user_subscription(bot: Bot, user_id: int, channel_id: int) -> bool:
    """
    Foydalanuvchining bitta kanalga a'zoligini tekshirish
    """
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except Exception as e:
        logging.error(f"A'zolik tekshirishda xatolik: {e}")
        return False

async def check_user_all_subscriptions(bot: Bot, user_id: int) -> bool:
    """
    Foydalanuvchining barcha majburiy kanallarga a'zoligini tekshirish
    """
    channels = await get_all_channels()
    
    for channel in channels:
        if not await check_user_subscription(bot, user_id, channel.channel_id):
            return False
    
    return True

# Callback handler'lar
async def handle_subscription_check(callback: CallbackQuery, bot: Bot):
    """
    A'zolikni tekshirish callback handler'i
    """
    user_id = callback.from_user.id
    
    # Barcha kanallarga a'zolikni tekshirish
    is_subscribed = await check_user_all_subscriptions(bot, user_id)
    
    if is_subscribed:
        # Agar a'zo bo'lsa
        await callback.answer("✅ Tabriklaymiz! Siz barcha kanallarga a'zo bo'lgansiz!", show_alert=True)
        # Xabarni o'chirish (ixtiyoriy)
        try:
            await callback.message.delete()
        except:
            pass
    else:
        # Agar hali ham a'zo bo'lmasa
        await callback.answer("❌ Siz hali ham barcha kanallarga a'zo bo'lmagansiz!", show_alert=True)

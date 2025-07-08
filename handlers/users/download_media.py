import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
from collections import deque
import aiogram
from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InputMediaVideo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.chat_action import ChatActionSender
from aiogram.exceptions import TelegramRetryAfter
from filters.video_filter import VideoTypeFilter
import time
from utils.lang import lang as LANGUAGES
# Import required modules
from .youtube import download_video, download_audio, get_video_info, is_valid_youtube_url, format_duration, format_file_size
from .instagram import download_instagram_video
from .tiktok import download_tiktok_video, is_tiktok_url, get_tiktok_info, cleanup_file

# Language configuration

router = Router()

# User languages
user_languages: Dict[int, str] = {}
# Rate limiting and queue system
user_download_history: Dict[int, List[datetime]] = {}
download_queue = deque()
last_progress_update = {}
progress_cache = {}
MAX_DOWNLOADS_PER_HOUR = 20
MAX_CONCURRENT_DOWNLOADS = 10
current_downloads = 0

def get_user_language(user_id: int) -> str:
    """Get user language"""
    return user_languages.get(user_id, "uz")  # Default: Uzbek

def get_text(user_id: int, key: str, **kwargs) -> str:
    """Get text in user's language"""
    lang = get_user_language(user_id)
    text = LANGUAGES[lang].get(key, LANGUAGES["uz"].get(key, key))
    return text.format(**kwargs) if kwargs else text



async def process_download_queue():
    """Process download queue"""
    global current_downloads
    
    while True:
        if download_queue and current_downloads < MAX_CONCURRENT_DOWNLOADS:
            task = download_queue.popleft()
            current_downloads += 1
            asyncio.create_task(task())
        await asyncio.sleep(0.1)

def check_rate_limit(user_id: int) -> bool:
    """Check user rate limit"""
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)
    
    if user_id not in user_download_history:
        user_download_history[user_id] = []
    
    user_download_history[user_id] = [
        download_time for download_time in user_download_history[user_id]
        if download_time > hour_ago
    ]
    
    return len(user_download_history[user_id]) < MAX_DOWNLOADS_PER_HOUR

def get_remaining_downloads(user_id: int) -> int:
    """Calculate remaining downloads"""
    if user_id not in user_download_history:
        return MAX_DOWNLOADS_PER_HOUR
    
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)
    
    recent_downloads = [
        download_time for download_time in user_download_history[user_id]
        if download_time > hour_ago
    ]
    
    return max(0, MAX_DOWNLOADS_PER_HOUR - len(recent_downloads))

async def update_user_download_history(user_id: int):
    """Update user download history"""
    if user_id not in user_download_history:
        user_download_history[user_id] = []
    user_download_history[user_id].append(datetime.now())

async def cleanup_after_delay(file_path: str, delay_seconds: int = 1):
    """Delete file after delay"""
    await asyncio.sleep(delay_seconds)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ File deleted: {file_path}")
    except Exception as e:
        print(f"❌ Error deleting file: {e}")

def clear_progress_cache(chat_id=None):
    """Clear progress cache"""
    global progress_cache
    if chat_id:
        keys_to_remove = [key for key in progress_cache if key.startswith(f"{chat_id}_")]
        for key in keys_to_remove:
            del progress_cache[key]
    else:
        progress_cache.clear()

def rate_limit_decorator(max_calls=3, period=60):
    """Rate limit decorator"""
    def decorator(func):
        call_times = {}
        
        async def wrapper(*args, **kwargs):
            if args and hasattr(args[0], 'chat'):
                chat_id = args[0].chat.id
            else:
                return await func(*args, **kwargs)
            
            current_time = time.time()
            
            if chat_id in call_times:
                call_times[chat_id] = [t for t in call_times[chat_id] if current_time - t < period]
            else:
                call_times[chat_id] = []
            
            if len(call_times[chat_id]) >= max_calls:
                return
            
            call_times[chat_id].append(current_time)
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

@rate_limit_decorator(max_calls=5, period=30)
async def send_progress_update(message: types.Message, progress_msg: types.Message, progress: float, platform: str):
    """Update progress"""
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        progress_percent = int(progress * 100)
        
        important_points = [0, 25, 50, 75, 100]
        
        closest_point = None
        for point in important_points:
            if abs(progress_percent - point) <= 8:
                closest_point = point
                break
        
        if closest_point is None:
            return
        
        cache_key = f"{chat_id}_{platform}"
        if cache_key in progress_cache and progress_cache[cache_key] == closest_point:
            return
        
        filled = min(10, int(progress * 10))
        progress_bar = "🟦" * filled + "⬜" * (10 - filled)
        
        text = (
            f"📥 <b>{get_text(user_id, 'downloading', platform=platform)}</b>\n\n"
            f"{progress_bar} {progress_percent}%\n\n"
            f"⏳ {get_text(user_id, 'queue_added').split('.')[1].strip()}"
        )
        
        try:
            await progress_msg.edit_text(text, parse_mode="HTML")
            progress_cache[cache_key] = closest_point
        except Exception:
            pass
            
    except Exception:
        pass


@router.message(Command('download'))
async def download_command(message: types.Message):
    """Download command"""
    user_id = message.from_user.id
    remaining = get_remaining_downloads(user_id)
    await message.reply(
        get_text(user_id, 'download_help', remaining=remaining),
        parse_mode="HTML"
    )

@router.message(Command('limit'))
async def limit_command(message: types.Message):
    """Limit command"""
    user_id = message.from_user.id
    remaining = get_remaining_downloads(user_id)
    await message.answer_sticker("CAACAgEAAxkBAAEO3z5oa7Bk74ZFQroBHztlxhwOr0zr6QACigIAApFJIEQVpamIL42sCjYE")
    await message.reply(
        get_text(user_id, 'limit_info', remaining=remaining),
        parse_mode="HTML"
    )

# YouTube handlers
@router.message(VideoTypeFilter(platform="youtube_short"))
async def download_youtube(message: types.Message):
    """YouTube download handler"""
    url = message.text.strip()
    user_id = message.from_user.id
    
    if not is_valid_youtube_url(url):
        await message.answer_sticker("CAACAgEAAxkBAAEO30Boa7Cyzy89w13FoJDHg_WsqLs6MQACpgEAAp-ZWEU7P-6NXtpGaTYE")
        await message.reply(get_text(user_id, 'invalid_url', platform="YouTube"))
        return
    
    download_queue.append(lambda: handle_youtube_download(message, url))
    yuklab_olish_navbati_xabari = await message.reply(get_text(user_id, 'queue_added'))

async def handle_youtube_download(message: types.Message, url: str):
    """Handle YouTube video download"""
    user_id = message.from_user.id
    
    if not check_rate_limit(user_id):
        await message.answer_sticker("CAACAgEAAxkBAAEO30Boa7Cyzy89w13FoJDHg_WsqLs6MQACpgEAAp-ZWEU7P-6NXtpGaTYE")
        await message.reply(get_text(user_id, 'rate_limit_exceeded'), parse_mode="HTML")
        return
    
    progress_msg = await message.reply(
        f"📥 {get_text(user_id, 'downloading', platform='YouTube')}\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%"
    )
    sticker = await message.answer_sticker("CAACAgEAAxkBAAEO30Roa7D42wTnvGCUy4mjYjgycWnHgAACgAIAAqFjGUSrWD-iBcJN3DYE")
    try:
        info = get_video_info(url)
        if 'error' in info:
            await progress_msg.edit_text(get_text(user_id, 'download_error', error=info['error']))
            await sticker.delete()
            return
        
        loop = asyncio.get_event_loop()
        
        def progress_callback(progress):
            asyncio.run_coroutine_threadsafe(
                send_progress_update(message, progress_msg, progress, "YouTube"),
                loop
            )
        
        result = await asyncio.to_thread(
            download_video,
            url,
            user_id=user_id,
            progress_hook=progress_callback
        )
        
        if result['success']:
            await progress_msg.edit_text(get_text(user_id, 'uploading'))
            
            await sticker.delete()
            
            video_file = FSInputFile(result['file_path'])
            caption = (
                f"📹 <b>{result['title']}</b>\n"
                f"👤 {result['uploader']}\n"
                f"⏱️ {format_duration(result['duration'])}\n"
                f"📊 {format_file_size(result['file_size'])}"
            )
            
            async with ChatActionSender.upload_video(chat_id=message.chat.id, bot=message.bot):
                await message.reply_video(
                    video=video_file,
                    caption=caption,
                    parse_mode="HTML"
                )
            await message.answer_sticker("CAACAgEAAxkBAAEO30toa7F5MRpoyDEB96MzPg1OYRxL9wAC-gEAAoyxIER4c3iI53gcxDYE")
            await progress_msg.delete()
            await update_user_download_history(user_id)
            
            asyncio.create_task(cleanup_after_delay(result['file_path'], 1))
        else:
            await progress_msg.edit_text(get_text(user_id, 'download_error', error=result['error']))

    except Exception as e:
        await progress_msg.edit_text(get_text(user_id, 'unexpected_error', error=str(e)))
    
    finally:
        global current_downloads
        current_downloads = max(0, current_downloads - 1)

# Instagram handlers
@router.message(VideoTypeFilter(platform="instagram_reel"))
async def download_instagram(message: types.Message):
    """Instagram download handler"""
    url = message.text.strip()
    user_id = message.from_user.id
    
    download_queue.append(lambda: handle_instagram_download(message, url))
    await message.reply(get_text(user_id, 'queue_added'))

async def handle_instagram_download(message: types.Message, url: str):
    """Handle Instagram video download"""
    user_id = message.from_user.id
    
    if not check_rate_limit(user_id):
        await message.answer_sticker("CAACAgEAAxkBAAEO30Boa7Cyzy89w13FoJDHg_WsqLs6MQACpgEAAp-ZWEU7P-6NXtpGaTYE")
        await message.reply(get_text(user_id, 'rate_limit_exceeded'), parse_mode="HTML")
        return
    
    progress_msg = await message.reply(
        f"📥 {get_text(user_id, 'downloading', platform='Instagram')}\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%"
    )
    sticker = await message.answer_sticker("CAACAgEAAxkBAAEO30Roa7D42wTnvGCUy4mjYjgycWnHgAACgAIAAqFjGUSrWD-iBcJN3DYE")
    try:
        # Get Instagram credentials from environment variables
        username = os.getenv("INSTAGRAM_USERNAME", "INSTA_USERNAME_KIRIT")
        password = os.getenv("INSTAGRAM_PASSWORD", "INSTA_PASSWORD_KIRIT")
        
        loop = asyncio.get_event_loop()
        
        def progress_callback(progress):
            asyncio.run_coroutine_threadsafe(
                send_progress_update(message, progress_msg, progress, "Instagram"),
                loop
            )
        
        result = await asyncio.to_thread(
            download_instagram_video, 
            url, 
            username, 
            password,
            progress_callback=progress_callback,
            debug=False
        )
        
        if result:
            await progress_msg.edit_text(get_text(user_id, 'uploading'))
            
            video_file = FSInputFile(result)
            await sticker.delete()
            
            async with ChatActionSender.upload_video(chat_id=message.chat.id, bot=message.bot):
                await message.reply_video(
                    video=video_file,
                    caption="📱 <b>Instagram Video</b>",
                    parse_mode="HTML"
                )
            
            await progress_msg.delete()
            await message.answer_sticker("CAACAgEAAxkBAAEO30toa7F5MRpoyDEB96MzPg1OYRxL9wAC-gEAAoyxIER4c3iI53gcxDYE")
            await update_user_download_history(user_id)
            
            asyncio.create_task(cleanup_after_delay(result, 1))
        else:
            await progress_msg.edit_text(get_text(user_id, 'download_error', error="Failed to download video"))
            
    except Exception as e:  
        await progress_msg.edit_text(get_text(user_id, 'unexpected_error', error=str(e)))
    finally:
        global current_downloads
        current_downloads = max(0, current_downloads - 1)

# TikTok handlers
@router.message(VideoTypeFilter(platform="tiktok"))
async def download_tiktok(message: types.Message):
    """TikTok download handler"""
    url = message.text.strip()
    user_id = message.from_user.id
    
    if not is_tiktok_url(url):
        await message.reply(get_text(user_id, 'invalid_url', platform="TikTok"))
        return
    
    download_queue.append(lambda: handle_tiktok_download(message, url))
    await message.reply(get_text(user_id, 'queue_added'))

async def handle_tiktok_download(message: types.Message, url: str):
    """Handle TikTok video download"""
    user_id = message.from_user.id
    
    if not check_rate_limit(user_id):
        await message.reply(get_text(user_id, 'rate_limit_exceeded'), parse_mode="HTML")
        return
    
    progress_msg = await message.reply(
        f"📥 {get_text(user_id, 'downloading', platform='TikTok')}\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%"
    )
    
    try:
        info = await asyncio.to_thread(get_tiktok_info, url)
        
        loop = asyncio.get_event_loop()
        
        def progress_callback(progress):
            asyncio.run_coroutine_threadsafe(
                send_progress_update(message, progress_msg, progress, "TikTok"),
                loop
            )
        
        result = await asyncio.to_thread(
            download_tiktok_video, 
            url, 
            output_dir=f"downloads/{user_id}",
            progress_callback=progress_callback
        )
        
        if result['success']:
            await progress_msg.edit_text(get_text(user_id, 'uploading'))
            
            video_file = FSInputFile(result['file_path'])
            
            caption = "🎵 <b>TikTok Video</b>\n"
            if info:
                caption += (
                    f"📹 {info['title']}\n"
                    f"👤 {info['uploader']}\n"
                    f"⏱️ {info['duration']} seconds"
                )
            
            async with ChatActionSender.upload_video(chat_id=message.chat.id, bot=message.bot):
                await message.reply_video(
                    video=video_file,
                    caption=caption,
                    parse_mode="HTML"
                )
            
            await progress_msg.delete()
            await update_user_download_history(user_id)
            
            asyncio.create_task(cleanup_after_delay(result['file_path'], 1))
        else:
            await progress_msg.edit_text(get_text(user_id, 'download_error', error=result['error']))
            
    except Exception as e:
        await progress_msg.edit_text(get_text(user_id, 'unexpected_error', error=str(e)))
    finally:
        global current_downloads
        current_downloads = max(0, current_downloads - 1)

# Audio handlers
@router.message(F.text.startswith(("🎵", "/audio")))
async def download_audio_handler(message: types.Message):
    """Audio download handler"""
    text = message.text.strip()
    user_id = message.from_user.id
    
    if text.startswith("🎵"):
        url = text[2:].strip()
    elif text.startswith("/audio"):
        url = text[6:].strip()
    else:
        await message.reply(get_text(user_id, 'audio_format_error'))
        return
    
    if not is_valid_youtube_url(url):
        await message.reply(get_text(user_id, 'invalid_url', platform="YouTube"))
        return
    
    download_queue.append(lambda: handle_audio_download(message, url))
    await message.reply(get_text(user_id, 'queue_added'))

async def handle_audio_download(message: types.Message, url: str):
    """Handle audio download"""
    user_id = message.from_user.id
    
    if not check_rate_limit(user_id):
        await message.reply(get_text(user_id, 'audio_limit_exceeded'), parse_mode="HTML")
        return
    
    progress_msg = await message.reply(
        f"🎵 {get_text(user_id, 'audio_downloading')}\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%"
    )
    
    try:
        loop = asyncio.get_event_loop()
        
        def progress_callback(progress):
            asyncio.run_coroutine_threadsafe(
                send_progress_update(message, progress_msg, progress, "YouTube Audio"),
                loop
            )
        
        result = await asyncio.to_thread(
            download_audio, 
            url, 
            user_id=user_id,
            progress_hook=progress_callback
        )
        
        if result['success']:
            await progress_msg.edit_text(get_text(user_id, 'audio_uploading'))
            
            audio_file = FSInputFile(result['file_path'])
            
            caption = (
                f"🎵 <b>{result['title']}</b>\n"
                f"📊 {format_file_size(result['file_size'])}"
            )
            
            async with ChatActionSender.upload_audio(chat_id=message.chat.id, bot=message.bot):
                await message.reply_audio(
                    audio=audio_file,
                    caption=caption,
                    parse_mode="HTML"
                )
            
            await progress_msg.delete()
            await update_user_download_history(user_id)
            
            asyncio.create_task(cleanup_after_delay(result['file_path'], 1))
        else:
            await progress_msg.edit_text(get_text(user_id, 'download_error', error=result['error']))
            
    except Exception as e:
        await progress_msg.edit_text(get_text(user_id, 'unexpected_error', error=str(e)))
    finally:
        global current_downloads
        current_downloads = max(0, current_downloads - 1)

# Other handlers
@router.message(VideoTypeFilter(platform="likee"))
async def download_likee(message: types.Message):
    """Likee download handler"""
    user_id = message.from_user.id
    await message.reply(
        get_text(user_id, 'unsupported_platform', platform="Likee"),
        parse_mode="HTML"
    )

@router.message(F.text.contains("http"))
async def handle_unknown_url(message: types.Message):
    """Unknown URL handler"""
    user_id = message.from_user.id
    await message.reply(
        get_text(user_id, 'unknown_url'),
        parse_mode="HTML"
    )

# Start queue processing
async def start_queue_processing():
    """Start processing the download queue"""
    asyncio.create_task(process_download_queue())
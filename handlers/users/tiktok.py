import yt_dlp
import os
import tempfile
from pathlib import Path

def download_tiktok_video(url, output_dir="downloads"):
    """
    TikTok videosini yuklab olish funksiyasi
    
    Args:
        url (str): TikTok video URL
        output_dir (str): Yuklab olinadigan papka
    
    Returns:
        dict: {
            'success': bool,
            'file_path': str or None,
            'error': str or None,
            'video_info': dict or None
        }
    """
    try:
        # Papka yaratish
        Path(output_dir).mkdir(exist_ok=True)
        
        # yt-dlp sozlamalari
        ydl_opts = {
            'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
            'format': 'best[height<=720]',  # 720p gacha
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Video ma'lumotlarini olish
            info = ydl.extract_info(url, download=False)
            
            # Video yuklab olish
            ydl.download([url])
            
            # Fayl nomini aniqlash
            filename = ydl.prepare_filename(info)
            
            return {
                'success': True,
                'file_path': filename,
                'error': None,
                'video_info': {
                    'title': info.get('title', 'Unknown'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0)
                }
            }
            
    except Exception as e:
        return {
            'success': False,
            'file_path': None,
            'error': str(e),
            'video_info': None
        }

def download_tiktok_to_temp(url):
    """
    TikTok videosini vaqtinchalik papkaga yuklab olish
    Telegram bot uchun qulay
    
    Args:
        url (str): TikTok video URL
    
    Returns:
        dict: download natijasi
    """
    temp_dir = tempfile.mkdtemp()
    return download_tiktok_video(url, temp_dir)

def get_tiktok_info(url):
    """
    TikTok video ma'lumotlarini olish (yuklab olmasdan)
    
    Args:
        url (str): TikTok video URL
    
    Returns:
        dict: video ma'lumotlari yoki None
    """
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return {
                'title': info.get('title', 'Unknown'),
                'uploader': info.get('uploader', 'Unknown'),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'description': info.get('description', '')[:100] + '...' if info.get('description') else ''
            }
            
    except Exception as e:
        return None

def is_tiktok_url(url):
    """
    URL TikTok ekanligini tekshirish
    
    Args:
        url (str): tekshiriladigan URL
    
    Returns:
        bool: True agar TikTok URL bo'lsa
    """
    tiktok_domains = [
        'tiktok.com',
        'www.tiktok.com',
        'vm.tiktok.com',
        'm.tiktok.com'
    ]
    
    return any(domain in url.lower() for domain in tiktok_domains)

def cleanup_file(file_path):
    """
    Faylni o'chirish (yuklab olingandan keyin)
    
    Args:
        file_path (str): o'chiriladigan fayl yo'li
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except:
        pass
    return False
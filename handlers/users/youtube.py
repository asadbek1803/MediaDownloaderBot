import yt_dlp
import os
from pathlib import Path
import math
import time


# YouTube download function - optimizatsiyalangan
def download_video(url, user_id=None, progress_hook=None, quality='best'):
    """
    YouTube video yuklash funksiyasi - Optimizatsiyalangan progress hook bilan
    """
    try:
        # Download papkasini yaratish
        if user_id:
            download_dir = Path(f"downloads/{user_id}")
        else:
            download_dir = Path("downloads")
        
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # Progress hisobotlari uchun klass - optimizatsiyalangan
        class ProgressLogger:
            def __init__(self):
                self.last_progress = 0
                self.last_update_time = 0
            
            def progress_hook(self, d):
                if progress_hook and d['status'] == 'downloading':
                    current_time = time.time()
                    
                    # Progressni 0-1 oralig'ida hisoblash
                    if 'total_bytes' in d:
                        progress = d['downloaded_bytes'] / d['total_bytes']
                    elif 'total_bytes_estimate' in d:
                        progress = d['downloaded_bytes'] / d['total_bytes_estimate']
                    else:
                        progress = 0
                    
                    # Progress faqat 10% o'zgarganda yoki 5 sekundda bir marta yuborish
                    progress_diff = abs(progress - self.last_progress)
                    time_diff = current_time - self.last_update_time
                    
                    if progress_diff >= 0.1 or time_diff >= 5 or progress >= 1:
                        try:
                            progress_hook(progress)
                            self.last_progress = progress
                            self.last_update_time = current_time
                        except Exception as e:
                            pass
        
        progress_logger = ProgressLogger()
        
        # yt-dlp sozlamalari
        ydl_opts = {
            'format': f'{quality}[filesize<50M]/best',
            'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_logger.progress_hook],
        }
        
        # Video ma'lumotlarini olish
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'Unknown')
            
            # Uzunlik tekshiruvi (10 daqiqadan uzun bo'lmasin)
            if duration > 600:  # 10 daqiqa
                return {
                    'success': False,
                    'error': 'Video juda uzun (10 daqiqadan ortiq)',
                    'duration': duration
                }
        
        # Videoni yuklash
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Yuklangan faylni topish
        files = list(download_dir.glob('*'))
        if not files:
            return {
                'success': False,
                'error': 'Fayl yuklanmadi'
            }
        
        # Eng oxirgi yuklangan fayl
        file_path = max(files, key=lambda f: f.stat().st_mtime)
        
        return {
            'success': True,
            'file_path': str(file_path),
            'title': title,
            'duration': duration,
            'uploader': uploader,
            'file_size': file_path.stat().st_size
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }



def download_audio(url, user_id=None, progress_hook=None):
    """
    YouTube audio yuklash funksiyasi - Progress hook bilan
    
    Args:
        url: YouTube video URL
        user_id: User ID (ixtiyoriy)
        progress_hook: Progressni qaytarish uchun funksiya
    
    Returns:
        dict: {
            'success': bool,
            'file_path': str,
            'title': str,
            'file_size': int,
            'error': str
        }
    """
    try:
        # Download papkasini yaratish
        if user_id:
            download_dir = Path(f"downloads/{user_id}")
        else:
            download_dir = Path("downloads")
        
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # Progress hisobotlari uchun klass
        class ProgressLogger:
            def __init__(self):
                self.last_progress = 0
            
            def progress_hook(self, d):
                if progress_hook and d['status'] == 'downloading':
                    # Progressni 0-1 oralig'ida hisoblash
                    if 'total_bytes' in d:
                        progress = d['downloaded_bytes'] / d['total_bytes']
                    elif 'total_bytes_estimate' in d:
                        progress = d['downloaded_bytes'] / d['total_bytes_estimate']
                    else:
                        progress = 0
                    
                    # Progress faqat 5% o'zgarganda yoki tugallanganda yuborish
                    if (math.floor(progress * 20) > math.floor(self.last_progress * 20)) or progress == 1:
                        progress_hook(progress)
                        self.last_progress = progress
        
        progress_logger = ProgressLogger()
        
        # yt-dlp sozlamalari
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_logger.progress_hook],
        }
        
        # Video ma'lumotlarini olish
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            
            ydl.download([url])
        
        # MP3 faylini topish
        files = list(download_dir.glob('*.mp3'))
        if not files:
            return {
                'success': False,
                'error': 'Audio fayl yuklanmadi'
            }
        
        # Eng oxirgi yuklangan MP3
        file_path = max(files, key=lambda f: f.stat().st_mtime)
        
        return {
            'success': True,
            'file_path': str(file_path),
            'title': title,
            'file_size': file_path.stat().st_size
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_video_info(url):
    """
    Video haqida ma'lumot olish (yuklamasdan)
    
    Args:
        url: YouTube video URL
    
    Returns:
        dict: Video ma'lumotlari yoki None
    """
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', 'Unknown'),
                'description': info.get('description', '')[:200] + '...' if info.get('description') else '',
                'thumbnail': info.get('thumbnail', ''),
                'webpage_url': info.get('webpage_url', url)
            }
            
    except Exception as e:
        return {
            'error': str(e)
        }

def is_valid_youtube_url(url):
    """
    YouTube URL ekanligini tekshirish
    
    Args:
        url: Tekshiriladigan URL
        
    Returns:
        bool: True agar valid YouTube URL bo'lsa
    """
    youtube_domains = [
        'youtube.com', 'youtu.be', 'www.youtube.com',
        'm.youtube.com', 'music.youtube.com'
    ]
    
    return any(domain in url for domain in youtube_domains)

def format_duration(seconds):
    """
    Soniyani formatlash (HH:MM:SS)
    
    Args:
        seconds: Soniya
        
    Returns:
        str: Formatlangan vaqt
    """
    if not seconds:
        return "0:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def format_file_size(size_bytes):
    """
    Fayl hajmini formatlash
    
    Args:
        size_bytes: Bayt hajmi
        
    Returns:
        str: Formatlangan hajm
    """
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} TB"

def clean_filename(filename):
    """
    Fayl nomini tozalash
    
    Args:
        filename: Fayl nomi
        
    Returns:
        str: Tozalangan fayl nomi
    """
    import re
    # Noto'g'ri belgilarni o'chirish
    clean_name = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Ortiqcha bo'shliqlarni o'chirish
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    return clean_name
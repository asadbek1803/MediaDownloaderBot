import os
import tempfile
import requests
import instaloader
import shutil
import logging
from typing import Optional, Dict, Union
from yt_dlp import YoutubeDL
import yt_dlp
from pathlib import Path

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB Telegram limit

logger = logging.getLogger(__name__)

class MediaDownloader:
    def __init__(self):
        self.temp_dir = None
    
    def download_media(self, url: str) -> Dict[str, Union[str, bool, Dict]]:
        """
        Universal media downloader that handles YouTube, Instagram, and TikTok
        
        Args:
            url: The URL of the media to download
            
        Returns:
            Dictionary with:
            - success: bool
            - file_path: str (if successful)
            - error: str (if failed)
            - video_info: dict (if available)
        """
        try:
            # Create temp directory
            self.temp_dir = tempfile.mkdtemp()
            
            # Determine platform and download accordingly
            if "youtube.com" in url or "youtu.be" in url:
                return self._download_youtube(url)
            elif "instagram.com" in url:
                return self._download_instagram(url)
            elif "tiktok.com" in url:
                return self._download_tiktok(url)
            else:
                return {
                    'success': False,
                    'error': 'Unsupported URL platform',
                    'file_path': None,
                    'video_info': None
                }
                
        except Exception as e:
            # Clean up temp directory on error
            self._cleanup_temp_dir()
            return {
                'success': False,
                'error': str(e),
                'file_path': None,
                'video_info': None
            }
    
    def _download_youtube(url, user_id=None, quality='best'):
        """
        YouTube video yuklash funksiyasi
        
        Args:
            url: YouTube video URL
            user_id: User ID (ixtiyoriy)
            quality: Video sifati ('best', 'worst', 'bestaudio')
        
        Returns:
            dict: {
                'success': bool,
                'file_path': str,
                'title': str,
                'duration': int,
                'uploader': str,
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
            
            # yt-dlp sozlamalari
            ydl_opts = {
                'format': f'{quality}[filesize<50M]',  # 50MB dan kichik
                'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
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

    
    def _download_instagram(self, url: str) -> Dict:
        """Download Instagram post/reel/story"""
        try:
            L = instaloader.Instaloader(
                dirname_pattern=self.temp_dir,
                save_metadata=False,
                download_video_thumbnails=False,
                download_pictures=True,
                download_videos=True,
                download_comments=False,
                download_geotags=False,
                compress_json=False,
                quiet=True
            )
            
            # Get shortcode from URL
            shortcode = self._extract_instagram_shortcode(url)
            if not shortcode:
                return {
                    'success': False,
                    'error': 'Could not extract shortcode from URL',
                    'file_path': None,
                    'video_info': None
                }
            
            # Download the post
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target=post.owner_username)
            
            # Find the downloaded file
            file_path = self._find_downloaded_file(self.temp_dir)
            
            if not file_path:
                return {
                    'success': False,
                    'error': 'Downloaded file not found',
                    'file_path': None,
                    'video_info': None
                }
            
            return {
                'success': True,
                'file_path': file_path,
                'error': None,
                'video_info': {
                    'title': post.caption[:100] + '...' if post.caption else 'Instagram post',
                    'uploader': post.owner_username,
                    'duration': post.video_duration if post.is_video else 0,
                    'view_count': post.video_view_count if post.is_video else 0
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_path': None,
                'video_info': None
            }
    
    def _download_tiktok(self, url: str) -> Dict:
        """Download TikTok video using yt-dlp"""
        ydl_opts = {
            'outtmpl': os.path.join(self.temp_dir, '%(title).100s.%(ext)s'),
            'format': 'best[height<=720][filesize<50M]',
            'max_filesize': MAX_FILE_SIZE,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                # Get video info first
                info = ydl.extract_info(url, download=False)
                video_info = {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'thumbnail': info.get('thumbnail', ''),
                }
                
                # Download the video
                ydl.download([url])
                
                # Find the downloaded file
                file_path = self._find_downloaded_file(self.temp_dir)
                
                if not file_path:
                    return {
                        'success': False,
                        'error': 'Downloaded file not found',
                        'file_path': None,
                        'video_info': video_info
                    }
                
                return {
                    'success': True,
                    'file_path': file_path,
                    'error': None,
                    'video_info': video_info
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_path': None,
                'video_info': None
            }
    
    def _extract_instagram_shortcode(self, url: str) -> Optional[str]:
        """Extract shortcode from Instagram URL"""
        try:
            if "instagram.com" not in url:
                return None
            
            # Handle different URL formats
            if '/p/' in url:
                return url.split('/p/')[1].split('/')[0]
            elif '/reel/' in url:
                return url.split('/reel/')[1].split('/')[0]
            elif '/stories/' in url:
                return url.split('/stories/')[1].split('/')[0]
            elif '/tv/' in url:
                return url.split('/tv/')[1].split('/')[0]
            
            return None
        except Exception:
            return None
    
    def _find_downloaded_file(self, directory: str) -> Optional[str]:
        """Find the downloaded media file in directory"""
        try:
            if not os.path.exists(directory):
                return None
            
            # Look for video files first
            for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
                for file in os.listdir(directory):
                    if file.lower().endswith(ext):
                        return os.path.join(directory, file)
            
            # Then look for image files
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                for file in os.listdir(directory):
                    if file.lower().endswith(ext):
                        return os.path.join(directory, file)
            
            return None
        except Exception:
            return None
    
    def _cleanup_temp_dir(self):
        """Clean up the temp directory"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
        except Exception as e:
            logger.error(f"Error cleaning up temp directory: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        self._cleanup_temp_dir()

def format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS"""
    if not seconds:
        return "0:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def format_file_size(size_bytes: int) -> str:
    """Convert file size to human-readable format"""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} TB"

import instaloader
from instaloader import Post
import requests
import os
import time
import math

# Instagram download function - to'g'irlangan
# Instagram download function - optimizatsiyalangan
def download_instagram_video(instagram_url, username, password, progress_callback=None, debug=False):
    """
    Instagram URL dan video yuklab olish - Optimizatsiyalangan progress callback bilan
    """
    try:
        if debug:
            print("🔧 Instaloader yaratilmoqda...")
        
        # Instaloader yaratish
        L = instaloader.Instaloader(quiet=not debug)
        
        if debug:
            print("🔐 Login qilinmoqda...")
        
        # Login
        L.login(username, password)
        
        if debug:
            print("✅ Login muvaffaqiyatli")
        
        # Shortcode ajratib olish
        if '/p/' in instagram_url:
            shortcode = instagram_url.split('/p/')[1].split('/')[0]
        elif '/reels/' in instagram_url:
            shortcode = instagram_url.split('/reels/')[1].split('/')[0]
        elif '/reel/' in instagram_url:
            shortcode = instagram_url.split('/reel/')[1].split('/')[0]
        else:
            if debug:
                print("❌ Noto'g'ri URL format")
            return None
        
        if debug:
            print(f"🔍 Shortcode: {shortcode}")
        
        # Progress: 0% - boshlash
        if progress_callback:
            try:
                progress_callback(0.0)
            except:
                pass
        
        time.sleep(2)
        
        # Post ma'lumotlarini olish
        if debug:
            print("📱 Post ma'lumotlari olinmoqda...")
        
        post = Post.from_shortcode(L.context, shortcode)
        
        if debug:
            print("✅ Post ma'lumotlari olindi")
        
        # Progress: 25% - post ma'lumotlari olindi
        if progress_callback:
            try:
                progress_callback(0.25)
            except:
                pass
        
        # Video tekshirish
        if not post.is_video:
            if debug:
                print("❌ Bu post video emas")
            return None
        
        if debug:
            print("🎬 Video post tasdiqlandi")
        
        # Video URL va fayl nomi
        video_url = post.video_url
        filename = f"{shortcode}.mp4"
        
        if debug:
            print(f"📺 Video URL: {video_url[:50]}...")
            print(f"📁 Fayl nomi: {filename}")
        
        # Progress: 50% - video ma'lumotlari olindi
        if progress_callback:
            try:
                progress_callback(0.5)
            except:
                pass
        
        # Video yuklab olish
        if debug:
            print("⬇️ Video yuklab olinmoqda...")
        
        response = requests.get(video_url, stream=True, timeout=60)
        
        if response.status_code != 200:
            if debug:
                print(f"❌ Video yuklab olishda xatolik: {response.status_code}")
            return None
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        if debug:
            print(f"📊 Jami hajm: {total_size} bytes")
        
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    downloaded += len(chunk)
                    
                    # Progress yangilash - faqat 75% gacha
                    if progress_callback and total_size > 0:
                        try:
                            progress = min(0.75, 0.5 + (downloaded / total_size * 0.25))
                            progress_callback(progress)
                        except:
                            pass
        
        if debug:
            print("💾 Fayl yozildi")
        
        # Progress: 100% - tugallandi
        if progress_callback:
            try:
                progress_callback(1.0)
            except:
                pass
        
        # Fayl tekshirish
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            if debug:
                print(f"📊 Fayl hajmi: {file_size / 1024:.2f} KB")
            
            if file_size > 1000:  # 1KB dan katta
                if debug:
                    print("✅ Fayl hajmi yetarli")
                return filename
            else:
                if debug:
                    print("❌ Fayl juda kichik")
                os.remove(filename)
                return None
        else:
            if debug:
                print("❌ Fayl yaratilmadi")
            return None
        
    except Exception as e:
        if debug:
            print(f"❌ Xatolik: {e}")
        return None
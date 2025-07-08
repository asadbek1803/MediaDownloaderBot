from aiogram.filters import BaseFilter
from aiogram.types import Message
from urllib.parse import urlparse

class VideoTypeFilter(BaseFilter):
    def __init__(self, platform: str):
        self.platform = platform

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False

        try:
            url = message.text.strip().lower()
            parsed_url = urlparse(url)
            
            if not all([parsed_url.scheme, parsed_url.netloc]):
                return False

            if self.platform == "youtube_short":
                return ("youtube.com/shorts/" in url or 
                        ("youtu.be/" in url and "shorts" in url))
            elif self.platform == "instagram_reel":
                return ("instagram.com/reels/" in url or
                        "instagram.com/reel/" in url or 
                        "instagram.com/p/" in url)
            elif self.platform == "tiktok":
                return ("tiktok.com/" in url or 
                        "vm.tiktok.com/" in url or 
                        "vt.tiktok.com/" in url)
            elif self.platform == "likee":
                return ("likee.video/" in url or 
                        "likee.com/" in url)
            return False
        except:
            return False
"""
Da Editor - Image Scraper
==========================
1a. scrapes google images based on keywords
1b. uses playwright for reliable scraping
1c. filters for high-quality images only
"""

import os
import re
import time
import random
import hashlib
import requests
from typing import List, Optional
from urllib.parse import urlparse


class ImageScraper:
    """
    scrape high-quality images from google images
    
    1a. uses playwright for browser automation
    1b. filters by resolution
    1c. downloads and saves images
    """
    
    # domains we wanna avoid - stock photo sites with watermarks
    BLOCKED_DOMAINS = [
        "alamy.com", "shutterstock.com", "gettyimages.com", "istockphoto.com",
        "dreamstime.com", "123rf.com", "depositphotos.com", "bigstockphoto.com",
        "stockphoto.com", "canstockphoto.com", "fotolia.com", "pond5.com",
        "adobe.stock", "vectorstock.com", "megapixl.com", "picfair.com"
    ]
    
    # user agents to rotate
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
    ]
    
    def __init__(
        self,
        output_dir: str,
        min_width: int = 1000,
        min_height: int = 800,
        min_size_kb: int = 50
    ):
        self.output_dir = output_dir
        self.min_width = min_width
        self.min_height = min_height
        self.min_size_kb = min_size_kb
        
        os.makedirs(output_dir, exist_ok=True)
        print(f"[Scraper] ready - output: {output_dir}")
    
    def search(self, keyword: str, max_images: int = 5) -> List[str]:
        """
        1a. search for images by keyword
        returns list of paths to downloaded images
        """
        print(f"[Scraper] searching: {keyword}")
        
        # try playwright first, fall back to requests
        try:
            return self._search_playwright(keyword, max_images)
        except Exception as e:
            print(f"[Scraper] playwright failed: {e}, trying requests method")
            return self._search_requests(keyword, max_images)
    
    def _search_playwright(self, keyword: str, max_images: int) -> List[str]:
        """
        2a. use playwright to scrape google images
        this method is more reliable but slower
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("playwright not installed - run: pip install playwright && playwright install chromium")
        
        downloaded = []
        
        with sync_playwright() as p:
            # launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(self.USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            # go to google images
            search_url = f"https://www.google.com/search?q={keyword}&tbm=isch&tbs=isz:l"  # large images
            page.goto(search_url, wait_until="domcontentloaded")
            
            # wait for images to load
            time.sleep(2)
            
            # scroll to load more images
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(0.5)
            
            # find image elements
            image_elements = page.query_selector_all("img[data-src]")
            
            for img in image_elements[:max_images * 3]:  # check more than we need
                if len(downloaded) >= max_images:
                    break
                
                try:
                    # get the image URL
                    src = img.get_attribute("data-src") or img.get_attribute("src")
                    
                    if not src or not src.startswith("http"):
                        continue
                    
                    # check if from blocked domain
                    if self._is_blocked(src):
                        continue
                    
                    # download the image
                    path = self._download_image(src, keyword)
                    if path:
                        downloaded.append(path)
                        
                except Exception as e:
                    continue
            
            browser.close()
        
        print(f"[Scraper] downloaded {len(downloaded)} images for '{keyword}'")
        return downloaded
    
    def _search_requests(self, keyword: str, max_images: int) -> List[str]:
        """
        2b. fallback method using requests
        less reliable but doesn't need playwright
        """
        downloaded = []
        
        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        
        search_url = f"https://www.google.com/search?q={keyword}&tbm=isch&tbs=isz:l"
        
        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # extract image URLs using regex (hacky but works)
            # looking for data:image or https URLs in the response
            urls = re.findall(r'https://[^"\s]+\.(?:jpg|jpeg|png|webp)', response.text)
            
            for url in urls[:max_images * 3]:
                if len(downloaded) >= max_images:
                    break
                
                if self._is_blocked(url):
                    continue
                
                path = self._download_image(url, keyword)
                if path:
                    downloaded.append(path)
                    
        except Exception as e:
            print(f"[Scraper] requests method failed: {e}")
        
        return downloaded
    
    def _is_blocked(self, url: str) -> bool:
        """
        3a. check if URL is from a blocked domain
        """
        for domain in self.BLOCKED_DOMAINS:
            if domain in url.lower():
                return True
        return False
    
    def _download_image(self, url: str, keyword: str) -> Optional[str]:
        """
        3b. download image from URL and save to disk
        returns path if successful, None if failed
        """
        try:
            headers = {
                "User-Agent": random.choice(self.USER_AGENTS),
                "Accept": "image/*",
                "Referer": "https://www.google.com/"
            }
            
            response = requests.get(url, headers=headers, timeout=15, stream=True)
            response.raise_for_status()
            
            # check content type
            content_type = response.headers.get("content-type", "")
            if "image" not in content_type.lower():
                return None
            
            # check size
            content_length = int(response.headers.get("content-length", 0))
            if content_length > 0 and content_length < self.min_size_kb * 1024:
                return None
            
            # generate filename
            ext = self._get_extension(url, content_type)
            name_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            safe_keyword = "".join(c if c.isalnum() else "_" for c in keyword)[:20]
            filename = f"{safe_keyword}_{name_hash}.{ext}"
            filepath = os.path.join(self.output_dir, filename)
            
            # save to disk
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # verify it's a valid image and check dimensions
            if self._verify_image(filepath):
                print(f"[Scraper] saved: {filename}")
                return filepath
            else:
                os.unlink(filepath)
                return None
            
        except Exception as e:
            return None
    
    def _get_extension(self, url: str, content_type: str) -> str:
        """get file extension from URL or content type"""
        # try URL first
        path = urlparse(url).path.lower()
        if ".jpg" in path or ".jpeg" in path:
            return "jpg"
        elif ".png" in path:
            return "png"
        elif ".webp" in path:
            return "webp"
        
        # try content type
        if "jpeg" in content_type:
            return "jpg"
        elif "png" in content_type:
            return "png"
        elif "webp" in content_type:
            return "webp"
        
        return "jpg"  # default
    
    def _verify_image(self, path: str) -> bool:
        """
        4a. verify image is valid and meets size requirements
        """
        try:
            from PIL import Image
            
            with Image.open(path) as img:
                width, height = img.size
                
                if width < self.min_width or height < self.min_height:
                    print(f"[Scraper] skipped: {width}x{height} too small")
                    return False
                
                return True
                
        except Exception as e:
            return False


def test_scraper():
    """quick test"""
    import tempfile
    
    scraper = ImageScraper(
        output_dir=tempfile.mkdtemp(),
        min_width=500,  # lower for testing
        min_height=400
    )
    
    images = scraper.search("mountain landscape", max_images=2)
    print(f"[Test] Found {len(images)} images")
    
    for img in images:
        print(f"  - {img}")


if __name__ == "__main__":
    test_scraper()

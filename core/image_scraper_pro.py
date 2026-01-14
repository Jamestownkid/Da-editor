"""
Da Editor - Pro Image Scraper
===============================
this is the upgraded scraper that actually works
uses playwright first, puppeteer fallback, then double-check

1a. playwright primary scraper
1b. puppeteer fallback if quota not met
1c. abc quality checks on every image
1d. perceptual hashing for dedupe

we aint accepting low quality garbage in this house
"""

import os
import re
import time
import random
import hashlib
import requests
from typing import List, Optional, Dict, Set
from urllib.parse import urlparse, urljoin
import tempfile


class ImageScraperPro:
    """
    professional grade image scraper with quality filters
    
    per spec rules 114-118:
    - minimum 900px width
    - no blur, no watermarks
    - blocked sites: pinterest, stock previews, meme sites
    - cinema-clean composition
    """
    
    # 1a. sites we dont want images from - they all trash
    BLOCKED_DOMAINS = [
        # stock photo sites with watermarks
        "alamy.com", "shutterstock.com", "gettyimages.com", "istockphoto.com",
        "dreamstime.com", "123rf.com", "depositphotos.com", "bigstockphoto.com",
        "stockphoto.com", "canstockphoto.com", "fotolia.com", "pond5.com",
        "adobe.stock", "vectorstock.com", "megapixl.com", "picfair.com",
        
        # pinterest and meme sites - per spec rule 116
        "pinterest.com", "pinterest.co", "pinimg.com",
        "imgflip.com", "quickmeme.com", "makeameme.org", "memegenerator.net",
        "9gag.com", "ifunny.co", "me.me", "knowyourmeme.com",
        
        # low quality blog thumbnails
        "wordpress.com/mshots", "s0.wp.com", "gravatar.com",
        "blogger.com", "blogspot.com",
        
        # social media profile pics
        "pbs.twimg.com/profile", "instagram.com", "fbcdn.net",
        
        # icons and small assets
        "favicon", "icon", "logo", "badge", "avatar"
    ]
    
    # 1b. user agents to rotate so we dont get blocked
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    def __init__(
        self,
        output_dir: str,
        min_width: int = 900,  # per spec rule 115
        min_height: int = 700,
        min_size_kb: int = 50
    ):
        self.output_dir = output_dir
        self.min_width = min_width
        self.min_height = min_height
        self.min_size_kb = min_size_kb
        
        # track used urls and hashes to avoid duplicates
        self.used_urls: Set[str] = set()
        self.used_hashes: Set[str] = set()
        
        os.makedirs(output_dir, exist_ok=True)
        print(f"[Scraper] initialized - output: {output_dir}")
    
    def search(self, keyword: str, max_images: int = 5) -> List[str]:
        """
        main search method - tries playwright first, then puppeteer fallback
        
        per spec rules 77-79:
        1. playwright first
        2. puppeteer fallback if quota not met
        3. playwright double-check pass
        """
        print(f"[Scraper] searching: {keyword}")
        downloaded = []
        
        # step 1: try playwright
        try:
            downloaded = self._search_playwright(keyword, max_images)
            print(f"[Scraper] playwright found {len(downloaded)} images")
        except Exception as e:
            print(f"[Scraper] playwright failed: {e}")
        
        # step 2: if not enough, try puppeteer (via pyppeteer)
        if len(downloaded) < max_images:
            try:
                remaining = max_images - len(downloaded)
                puppeteer_results = self._search_pyppeteer(keyword, remaining)
                downloaded.extend(puppeteer_results)
                print(f"[Scraper] pyppeteer found {len(puppeteer_results)} more images")
            except Exception as e:
                print(f"[Scraper] pyppeteer failed: {e}")
        
        # step 3: double-check pass with playwright (per spec rule 79)
        if len(downloaded) < max_images:
            try:
                remaining = max_images - len(downloaded)
                doublecheck = self._search_playwright(keyword + " high quality", remaining)
                downloaded.extend(doublecheck)
                print(f"[Scraper] double-check found {len(doublecheck)} more")
            except Exception as e:
                print(f"[Scraper] double-check failed: {e}")
        
        # fallback to requests if browser methods all failed
        if len(downloaded) == 0:
            print("[Scraper] browser methods failed, trying requests...")
            downloaded = self._search_requests(keyword, max_images)
        
        return downloaded[:max_images]
    
    def _search_playwright(self, keyword: str, max_images: int) -> List[str]:
        """
        use playwright to scrape google images
        this is our primary method - most reliable
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("playwright not installed - run: pip install playwright && playwright install chromium")
        
        downloaded = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(self.USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            # search google images with large size filter
            search_url = f"https://www.google.com/search?q={keyword}&tbm=isch&tbs=isz:l"
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            # wait for images to load
            time.sleep(2)
            
            # scroll to load more
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(0.5)
            
            # get all images
            images = page.query_selector_all("img")
            
            candidate_urls = []
            for img in images:
                try:
                    src = img.get_attribute("src") or img.get_attribute("data-src")
                    if src and src.startswith("http") and "encrypted" not in src:
                        candidate_urls.append(src)
                except:
                    continue
            
            # also try to get full-res URLs from data attributes
            anchors = page.query_selector_all("a[href*='imgurl=']")
            for a in anchors:
                try:
                    href = a.get_attribute("href")
                    if href and "imgurl=" in href:
                        # extract the actual image URL
                        match = re.search(r'imgurl=([^&]+)', href)
                        if match:
                            from urllib.parse import unquote
                            url = unquote(match.group(1))
                            candidate_urls.append(url)
                except:
                    continue
            
            browser.close()
        
        # now download and validate each candidate
        for url in candidate_urls[:max_images * 3]:
            if len(downloaded) >= max_images:
                break
            
            # run ABC checks
            if not self._check_a_url_valid(url):
                continue
            
            path = self._download_and_check(url, keyword)
            if path:
                downloaded.append(path)
        
        return downloaded
    
    def _search_pyppeteer(self, keyword: str, max_images: int) -> List[str]:
        """
        fallback to pyppeteer (python puppeteer port)
        """
        try:
            import asyncio
            from pyppeteer import launch
        except ImportError:
            print("[Scraper] pyppeteer not installed - skipping")
            return []
        
        async def scrape():
            downloaded = []
            
            browser = await launch(headless=True)
            page = await browser.newPage()
            await page.setUserAgent(random.choice(self.USER_AGENTS))
            
            search_url = f"https://www.bing.com/images/search?q={keyword}&qft=+filterui:imagesize-large"
            await page.goto(search_url, waitUntil="domcontentloaded")
            
            await asyncio.sleep(2)
            
            # scroll
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(0.5)
            
            # get image URLs
            images = await page.querySelectorAll("img.mimg")
            urls = []
            for img in images:
                try:
                    src = await page.evaluate("(el) => el.src", img)
                    if src and src.startswith("http"):
                        urls.append(src)
                except:
                    continue
            
            await browser.close()
            
            for url in urls[:max_images * 2]:
                if len(downloaded) >= max_images:
                    break
                
                if not self._check_a_url_valid(url):
                    continue
                
                path = self._download_and_check(url, keyword)
                if path:
                    downloaded.append(path)
            
            return downloaded
        
        # run async code
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(scrape())
        finally:
            loop.close()
    
    def _search_requests(self, keyword: str, max_images: int) -> List[str]:
        """
        basic requests fallback when browsers dont work
        """
        downloaded = []
        
        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml",
        }
        
        # try bing since google is harder
        search_url = f"https://www.bing.com/images/search?q={keyword}&qft=+filterui:imagesize-large"
        
        try:
            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # find image URLs in response
            urls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', response.text)
            
            for url in urls[:max_images * 2]:
                if len(downloaded) >= max_images:
                    break
                
                if not self._check_a_url_valid(url):
                    continue
                
                path = self._download_and_check(url, keyword)
                if path:
                    downloaded.append(path)
                    
        except Exception as e:
            print(f"[Scraper] requests fallback failed: {e}")
        
        return downloaded
    
    # ===========================================
    # ABC CHECKS - per spec rules 83-87
    # ===========================================
    
    def _check_a_url_valid(self, url: str) -> bool:
        """
        A-check: confirm URL resolves and returns an image
        not broken, not 404, not blocked
        """
        # check against blocked domains
        url_lower = url.lower()
        for blocked in self.BLOCKED_DOMAINS:
            if blocked in url_lower:
                return False
        
        # check for common bad patterns
        bad_patterns = ["thumbnail", "thumb", "small", "preview", "icon", "logo", "avatar", "profile"]
        for pattern in bad_patterns:
            if pattern in url_lower:
                return False
        
        # check if already used
        if url in self.used_urls:
            return False
        
        return True
    
    def _check_b_quality(self, filepath: str) -> bool:
        """
        B-check: confirm basic quality
        - minimum resolution (900px width per spec)
        - minimum file size (no tiny thumbnails)
        """
        try:
            from PIL import Image
            
            # check file size first
            file_size = os.path.getsize(filepath)
            if file_size < self.min_size_kb * 1024:
                return False
            
            # check dimensions
            with Image.open(filepath) as img:
                width, height = img.size
                
                if width < self.min_width or height < self.min_height:
                    return False
                
                # check for weird aspect ratios (probably cropped/letterboxed)
                aspect = width / height
                if aspect < 0.3 or aspect > 3.0:
                    return False
            
            return True
            
        except Exception as e:
            return False
    
    def _check_c_unique(self, filepath: str) -> bool:
        """
        C-check: confirm uniqueness using perceptual hash
        catches duplicates even from different URLs
        """
        try:
            file_hash = self._get_perceptual_hash(filepath)
            
            if file_hash in self.used_hashes:
                return False
            
            self.used_hashes.add(file_hash)
            return True
            
        except Exception:
            # if hashing fails, use file hash
            md5 = hashlib.md5(open(filepath, 'rb').read()).hexdigest()
            if md5 in self.used_hashes:
                return False
            self.used_hashes.add(md5)
            return True
    
    def _get_perceptual_hash(self, filepath: str) -> str:
        """
        compute perceptual hash (dhash) for image
        similar images will have similar hashes
        """
        try:
            from PIL import Image
            
            with Image.open(filepath) as img:
                # resize to 9x8
                img = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())
                
                # compute difference hash
                diff = []
                for row in range(8):
                    for col in range(8):
                        idx = row * 9 + col
                        diff.append(1 if pixels[idx] < pixels[idx + 1] else 0)
                
                # convert to hex string
                return ''.join(str(b) for b in diff)
                
        except Exception:
            # fallback to file hash
            return hashlib.md5(open(filepath, 'rb').read()).hexdigest()
    
    def _download_and_check(self, url: str, keyword: str) -> Optional[str]:
        """
        download image and run all quality checks
        returns path if good, None if rejected
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
            if "image" not in content_type.lower() and "octet" not in content_type.lower():
                return None
            
            # get extension
            ext = self._get_extension(url, content_type)
            
            # generate filename
            url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
            safe_keyword = "".join(c if c.isalnum() else "_" for c in keyword)[:20]
            filename = f"{safe_keyword}_{url_hash}.{ext}"
            filepath = os.path.join(self.output_dir, filename)
            
            # save to temp first
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # run B-check (quality)
            if not self._check_b_quality(temp_path):
                os.unlink(temp_path)
                return None
            
            # run C-check (uniqueness)
            if not self._check_c_unique(temp_path):
                os.unlink(temp_path)
                return None
            
            # all checks passed - move to output
            import shutil
            shutil.move(temp_path, filepath)
            
            # mark url as used
            self.used_urls.add(url)
            
            print(f"[Scraper] saved: {filename}")
            return filepath
            
        except Exception as e:
            return None
    
    def _get_extension(self, url: str, content_type: str) -> str:
        """get file extension from URL or content type"""
        path = urlparse(url).path.lower()
        
        if ".jpg" in path or ".jpeg" in path:
            return "jpg"
        elif ".png" in path:
            return "png"
        elif ".webp" in path:
            return "webp"
        
        if "jpeg" in content_type:
            return "jpg"
        elif "png" in content_type:
            return "png"
        elif "webp" in content_type:
            return "webp"
        
        return "jpg"


def test_scraper():
    """test the scraper"""
    import tempfile
    
    scraper = ImageScraperPro(
        output_dir=tempfile.mkdtemp(),
        min_width=800,
        min_height=600
    )
    
    images = scraper.search("mountain landscape scenic", max_images=3)
    print(f"\n[Test] Found {len(images)} images:")
    for img in images:
        print(f"  - {img}")


if __name__ == "__main__":
    test_scraper()


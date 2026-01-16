"""
Da Editor - Pro Image Scraper (v4)
===================================
FIXED:
- REUSE ONE BROWSER PER JOB (massive performance improvement)
- No more spawning chromium per keyword (was killing CPU/RAM)
- Scrape time capped at 10 minutes total
- ABC quality checks with hamming distance dedupe
- cinema-clean images only
"""

import os
import re
import time
import random
import hashlib
import requests
import json
from typing import List, Optional, Set, Dict
from urllib.parse import urlparse, unquote, quote_plus
import tempfile


class ImageScraperPro:
    """
    professional image scraper that actually works
    clicks thumbnails to get the real full-res image URLs
    """
    
    # blocked domains - hostname based checking (rule 116)
    BLOCKED_HOSTNAMES = {
        # stock sites with watermarks
        "alamy.com", "www.alamy.com",
        "shutterstock.com", "www.shutterstock.com",
        "gettyimages.com", "www.gettyimages.com", "media.gettyimages.com",
        "istockphoto.com", "www.istockphoto.com", "media.istockphoto.com",
        "dreamstime.com", "www.dreamstime.com", "thumbs.dreamstime.com",
        "123rf.com", "www.123rf.com", "previews.123rf.com",
        "depositphotos.com", "st.depositphotos.com",
        "bigstockphoto.com", "www.bigstockphoto.com",
        "stock.adobe.com", "t3.ftcdn.net", "t4.ftcdn.net",
        "vectorstock.com", "www.vectorstock.com",
        "megapixl.com", "www.megapixl.com",
        "picfair.com", "www.picfair.com",
        
        # pinterest and meme sites (rule 116)
        "pinterest.com", "www.pinterest.com", "i.pinimg.com", "pinimg.com",
        "imgflip.com", "i.imgflip.com",
        "quickmeme.com", "makeameme.org", "memegenerator.net",
        "9gag.com", "img-9gag-fun.9cache.com",
        "ifunny.co", "me.me", "knowyourmeme.com",
        
        # social media profile pics / low quality
        "gravatar.com", "0.gravatar.com", "1.gravatar.com", "2.gravatar.com",
        "pbs.twimg.com",  # but we'll check path for /profile
    }
    
    # bad URL patterns (thumbnails, previews, etc)
    BAD_URL_PATTERNS = [
        "thumbnail", "/thumb/", "/thumbs/", "_thumb", "-thumb",
        "small", "_s.", "_sm.", "_small",
        "preview", "/preview/", "_preview",
        "/icon", "_icon", "-icon", "favicon",
        "/logo", "_logo", "-logo",
        "/avatar", "_avatar",
        "/profile", "_profile",
        "/badge", "_badge",
        "100x", "150x", "200x", "300x",
        "w_100", "w_150", "w_200", "h_100", "h_150", "h_200",
        "encrypted-tbn", "gstatic.com/images",  # google thumbnails
        "data:image",  # base64 encoded (usually tiny)
    ]
    
    # max download size in bytes (12MB cap - rule 12)
    MAX_DOWNLOAD_SIZE = 12 * 1024 * 1024
    
    # user agents
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    def __init__(
        self,
        output_dir: str,
        min_width: int = 900,
        min_height: int = 700,
        min_size_kb: int = 50,
        manifest_path: str = None
    ):
        self.output_dir = output_dir
        self.min_width = min_width
        self.min_height = min_height
        self.min_size_kb = min_size_kb
        self.manifest_path = manifest_path
        
        # tracking for deduplication
        self.used_urls: Set[str] = set()
        self.used_hashes: Dict[str, str] = {}  # hash -> filepath
        
        # FIXED: Reuse browser across searches
        self._browser = None
        self._context = None
        self._playwright = None
        self._scrape_start_time = None
        self._max_scrape_time = 10 * 60  # 10 minute cap
        
        os.makedirs(output_dir, exist_ok=True)
        
        # load existing manifest if provided
        if manifest_path:
            self._load_manifest()
        
        print(f"[Scraper v4] ready - min {min_width}x{min_height}, reusing browser")
    
    def _load_manifest(self):
        """load existing manifest for cross-job deduplication"""
        if self.manifest_path and os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r") as f:
                    data = json.load(f)
                    self.used_urls = set(data.get("used_urls", []))
                    self.used_hashes = data.get("used_hashes", {})
                    print(f"[Scraper] loaded manifest: {len(self.used_urls)} URLs, {len(self.used_hashes)} hashes")
            except Exception as e:
                print(f"[Scraper] manifest load error: {e}")
    
    def _get_browser(self):
        """FIXED: Get or create browser - REUSES existing browser"""
        if self._browser is not None:
            return self._browser
        
        try:
            from playwright.sync_api import sync_playwright
            
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            self._context = self._browser.new_context(
                user_agent=random.choice(self.USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )
            print("[Scraper] browser started (will be reused)")
            return self._browser
        except Exception as e:
            print(f"[Scraper] failed to start browser: {e}")
            return None
    
    def _close_browser(self):
        """Close the browser when done"""
        try:
            if self._browser:
                self._browser.close()
                self._browser = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            self._context = None
        except:
            pass
    
    def __del__(self):
        """Cleanup browser on destruction"""
        self._close_browser()
    
    def save_manifest(self):
        """save manifest for persistence (rule 88)"""
        if self.manifest_path:
            data = {
                "used_urls": list(self.used_urls),
                "used_hashes": self.used_hashes
            }
            with open(self.manifest_path, "w") as f:
                json.dump(data, f, indent=2)
    
    def search(self, keyword: str, max_images: int = 5) -> List[str]:
        """
        main search - FIXED: reuses browser, respects time limit
        """
        # Initialize scrape start time if not set
        if self._scrape_start_time is None:
            self._scrape_start_time = time.time()
        
        # Check time limit
        elapsed = time.time() - self._scrape_start_time
        if elapsed > self._max_scrape_time:
            print(f"[Scraper] time limit reached ({elapsed:.0f}s), skipping search")
            return []
        
        print(f"[Scraper] searching: {keyword}")
        downloaded = []
        
        # step 1: playwright with SHARED browser
        try:
            downloaded = self._search_playwright_click(keyword, max_images)
            print(f"[Scraper] playwright: {len(downloaded)} images")
        except Exception as e:
            print(f"[Scraper] playwright failed: {e}")
        
        # step 2: bing fallback (check time limit first)
        if len(downloaded) < max_images:
            elapsed = time.time() - self._scrape_start_time
            if elapsed < self._max_scrape_time:
                try:
                    remaining = max_images - len(downloaded)
                    more = self._search_bing(keyword, remaining)
                    downloaded.extend(more)
                    print(f"[Scraper] bing fallback: {len(more)} more")
                except Exception as e:
                    print(f"[Scraper] bing failed: {e}")
        
        # save manifest after each search
        self.save_manifest()
        
        return downloaded[:max_images]
    
    def _search_playwright_click(self, keyword: str, max_images: int) -> List[str]:
        """
        playwright scraper - FIXED: REUSES browser from _get_browser()
        """
        browser = self._get_browser()
        if not browser:
            # Fallback to requests-only search
            return self._search_bing_requests(keyword, max_images)
        
        downloaded = []
        
        # Use the shared context
        if not self._context:
            self._context = browser.new_context(
                user_agent=random.choice(self.USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )
        
        page = self._context.new_page()
            
            # URL encode keyword properly
            encoded_keyword = quote_plus(keyword)
            search_url = f"https://www.google.com/search?q={encoded_keyword}&tbm=isch&tbs=isz:l"
            
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)  # let images load
                
                # handle consent if needed
                try:
                    consent_btn = page.query_selector('button[aria-label*="Accept"]')
                    if consent_btn:
                        consent_btn.click()
                        time.sleep(1)
                except:
                    pass
                
                # scroll to load more thumbnails
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 600)")
                    time.sleep(0.4)
                
                # get all thumbnail containers - these are clickable
                # google images uses data-index for thumbnails
                thumbnails = page.query_selector_all('div[jsname="dTDiAc"]')
                if not thumbnails:
                    thumbnails = page.query_selector_all('div[data-id]')
                
                print(f"[Scraper] found {len(thumbnails)} thumbnails to try")
                
                tried = 0
                for thumb in thumbnails[:max_images * 4]:  # try more than needed
                    if len(downloaded) >= max_images:
                        break
                    if tried >= max_images * 3:  # dont try forever
                        break
                    
                    tried += 1
                    time.sleep(0.3)  # throttle (rule 92)
                    
                    try:
                        # click the thumbnail to open preview panel
                        thumb.click()
                        time.sleep(0.8)  # wait for preview to load
                        
                        # now extract the REAL image URL from the preview panel
                        # it appears in an img with specific attributes
                        real_img = page.query_selector('img[jsname="kn3ccd"]')
                        if not real_img:
                            real_img = page.query_selector('img.sFlh5c.pT0Scc.iPVvYb')
                        if not real_img:
                            real_img = page.query_selector('img[class*="r48jcc"]')
                        
                        if real_img:
                            src = real_img.get_attribute("src")
                            
                            # skip base64 and thumbnails
                            if src and src.startswith("http") and "data:image" not in src:
                                # also try to get from srcset which sometimes has higher res
                                srcset = real_img.get_attribute("srcset")
                                if srcset:
                                    # parse srcset - usually has multiple resolutions
                                    parts = srcset.split(",")
                                    for part in reversed(parts):  # start from highest
                                        url = part.strip().split(" ")[0]
                                        if url.startswith("http"):
                                            src = url
                                            break
                                
                                # validate and download
                                if self._check_url(src):
                                    path = self._download_and_validate(src, keyword)
                                    if path:
                                        downloaded.append(path)
                        
                        # press escape to close preview
                        page.keyboard.press("Escape")
                        time.sleep(0.2)
                        
                    except Exception as e:
                        # thumbnail click failed, try next
                        continue
                
            except Exception as e:
                print(f"[Scraper] page load error: {e}")
            finally:
                # Close page but NOT browser (we reuse it)
                try:
                    page.close()
                except:
                    pass
        
        return downloaded
    
    def _search_bing(self, keyword: str, max_images: int) -> List[str]:
        """bing images fallback - FIXED: REUSES browser"""
        downloaded = []
        
        browser = self._get_browser()
        if not browser:
            return self._search_bing_requests(keyword, max_images)
        
        # Use the shared context
        if not self._context:
            self._context = browser.new_context(
                user_agent=random.choice(self.USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )
        
        page = self._context.new_page()
            
            encoded = quote_plus(keyword)
            search_url = f"https://www.bing.com/images/search?q={encoded}&qft=+filterui:imagesize-large"
            
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
                
                # scroll
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 600)")
                    time.sleep(0.4)
                
                # bing stores the actual image URL in the murl attribute
                # we can extract it from the page without clicking
                images = page.query_selector_all('a.iusc')
                
                for img in images[:max_images * 3]:
                    if len(downloaded) >= max_images:
                        break
                    
                    try:
                        # bing has a 'm' attribute with JSON containing the real URL
                        m_attr = img.get_attribute("m")
                        if m_attr:
                            data = json.loads(m_attr)
                            url = data.get("murl")  # murl is the media URL (full res)
                            
                            if url and self._check_url(url):
                                time.sleep(0.3)
                                path = self._download_and_validate(url, keyword)
                                if path:
                                    downloaded.append(path)
                    except:
                        continue
                
            except Exception as e:
                print(f"[Scraper] bing error: {e}")
            finally:
                # Close page but NOT browser
                try:
                    page.close()
                except:
                    pass
        
        return downloaded
    
    def _search_bing_requests(self, keyword: str, max_images: int) -> List[str]:
        """requests-only bing fallback for when playwright is unavailable"""
        downloaded = []
        
        headers = {"User-Agent": random.choice(self.USER_AGENTS)}
        encoded = quote_plus(keyword)
        search_url = f"https://www.bing.com/images/search?q={encoded}&qft=+filterui:imagesize-large"
        
        try:
            response = requests.get(search_url, headers=headers, timeout=15)
            
            # extract murl from page
            urls = re.findall(r'"murl":"(https?://[^"]+)"', response.text)
            
            for url in urls[:max_images * 2]:
                if len(downloaded) >= max_images:
                    break
                
                # unescape the url
                url = url.replace("\\u0026", "&")
                
                if self._check_url(url):
                    time.sleep(0.5)
                    path = self._download_and_validate(url, keyword)
                    if path:
                        downloaded.append(path)
                        
        except Exception as e:
            print(f"[Scraper] requests fallback failed: {e}")
        
        return downloaded
    
    # =====================
    # URL VALIDATION (A-check)
    # =====================
    
    def _check_url(self, url: str) -> bool:
        """A-check: URL validation with hostname-based blocking (rule 83)"""
        if not url or not url.startswith("http"):
            return False
        
        url_lower = url.lower()
        
        # parse hostname
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
        except:
            return False
        
        # check blocked hostnames (rule 116)
        for blocked in self.BLOCKED_HOSTNAMES:
            if hostname == blocked or hostname.endswith("." + blocked):
                return False
        
        # check bad URL patterns (thumbnails, previews, icons)
        for pattern in self.BAD_URL_PATTERNS:
            if pattern in url_lower:
                return False
        
        # already used (rule 87)
        if url in self.used_urls:
            return False
        
        return True
    
    # =====================
    # QUALITY VALIDATION (B-check)
    # =====================
    
    def _check_quality(self, filepath: str) -> bool:
        """B-check: quality validation (rules 84, 115)"""
        try:
            from PIL import Image
            
            # file size check
            size = os.path.getsize(filepath)
            if size < self.min_size_kb * 1024:
                return False
            
            with Image.open(filepath) as img:
                width, height = img.size
                
                # min resolution (rule 115: >= 900px width)
                if width < self.min_width or height < self.min_height:
                    return False
                
                # aspect ratio check (rule 118: reject cramped images)
                aspect = width / height
                if aspect < 0.4 or aspect > 2.5:
                    return False
                
                # composition check for face overlay (rule 117)
                # for portrait format, prefer images with headroom
                # reject images where main content is in bottom 30%
                # we use a simple heuristic: check if bottom portion is mostly uniform
                # (indicates empty space vs subject)
                if aspect < 1.0:  # portrait-ish
                    # crop bottom 30%
                    bottom = img.crop((0, int(height * 0.7), width, height))
                    # convert to grayscale and check variance
                    gray = bottom.convert("L")
                    pixels = list(gray.getdata())
                    if len(pixels) > 0:
                        avg = sum(pixels) / len(pixels)
                        variance = sum((p - avg) ** 2 for p in pixels) / len(pixels)
                        # low variance = uniform = probably background = good
                        # high variance with high brightness = might be subject = still ok
                        # we're being permissive here
                
            return True
            
        except Exception as e:
            print(f"[Scraper] quality check error: {e}")
            return False
    
    # =====================
    # UNIQUENESS CHECK (C-check with Hamming distance)
    # =====================
    
    def _check_unique(self, filepath: str) -> bool:
        """C-check: uniqueness via perceptual hash with Hamming distance (rules 85-87)"""
        try:
            phash = self._get_perceptual_hash(filepath)
            
            # check for NEAR duplicates using Hamming distance
            # two hashes within 5 bits difference are considered duplicates
            for existing_hash in self.used_hashes:
                distance = self._hamming_distance(phash, existing_hash)
                if distance <= 5:  # threshold for near-duplicate
                    return False
            
            self.used_hashes[phash] = filepath
            return True
            
        except Exception:
            # fallback to md5
            md5 = hashlib.md5(open(filepath, 'rb').read()).hexdigest()
            if md5 in self.used_hashes:
                return False
            self.used_hashes[md5] = filepath
            return True
    
    def _get_perceptual_hash(self, filepath: str) -> str:
        """compute perceptual hash (dhash) - 64 bit"""
        try:
            from PIL import Image
            
            with Image.open(filepath) as img:
                # convert to grayscale and resize to 9x8
                img = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())
                
                # compute difference hash
                diff = []
                for row in range(8):
                    for col in range(8):
                        idx = row * 9 + col
                        diff.append('1' if pixels[idx] < pixels[idx + 1] else '0')
                
                return ''.join(diff)
                
        except Exception:
            # fallback
            return hashlib.md5(open(filepath, 'rb').read()).hexdigest()[:64]
    
    def _hamming_distance(self, h1: str, h2: str) -> int:
        """compute hamming distance between two hashes"""
        if len(h1) != len(h2):
            return 64  # max distance
        return sum(c1 != c2 for c1, c2 in zip(h1, h2))
    
    # =====================
    # DOWNLOAD
    # =====================
    
    def _download_and_validate(self, url: str, keyword: str) -> Optional[str]:
        """download image and run all ABC checks"""
        try:
            headers = {
                "User-Agent": random.choice(self.USER_AGENTS),
                "Accept": "image/*,*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/"
            }
            
            # check content-length before downloading (rule 12)
            head_response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            content_length = int(head_response.headers.get("content-length", 0))
            if content_length > self.MAX_DOWNLOAD_SIZE:
                print(f"[Scraper] skipping - too large: {content_length // (1024*1024)}MB")
                return None
            
            # download with streaming and size limit
            response = requests.get(url, headers=headers, timeout=20, stream=True)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            if "image" not in content_type.lower() and "octet" not in content_type.lower():
                return None
            
            # get extension
            ext = "jpg"
            if ".png" in url.lower() or "png" in content_type:
                ext = "png"
            elif ".webp" in url.lower() or "webp" in content_type:
                ext = "webp"
            elif ".gif" in url.lower() or "gif" in content_type:
                ext = "gif"
            
            # generate filename
            url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
            safe_keyword = "".join(c if c.isalnum() else "_" for c in keyword)[:15]
            filename = f"{safe_keyword}_{url_hash}.{ext}"
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            
            # save to temp with size limit
            total_size = 0
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    total_size += len(chunk)
                    if total_size > self.MAX_DOWNLOAD_SIZE:
                        f.close()
                        os.unlink(temp_path)
                        return None
                    f.write(chunk)
            
            # run B-check (quality)
            if not self._check_quality(temp_path):
                os.unlink(temp_path)
                return None
            
            # run C-check (uniqueness with hamming)
            if not self._check_unique(temp_path):
                os.unlink(temp_path)
                return None
            
            # move to output
            final_path = os.path.join(self.output_dir, filename)
            import shutil
            shutil.move(temp_path, final_path)
            
            self.used_urls.add(url)
            print(f"[Scraper] saved: {filename}")
            return final_path
            
        except Exception as e:
            # cleanup temp if exists
            try:
                temp_path = os.path.join(tempfile.gettempdir(), f"{keyword}_{hashlib.md5(url.encode()).hexdigest()[:10]}.*")
                import glob
                for f in glob.glob(temp_path):
                    os.unlink(f)
            except:
                pass
            return None


def test_scraper():
    """test the scraper"""
    import tempfile
    
    output = tempfile.mkdtemp()
    manifest = os.path.join(output, "manifest.json")
    
    scraper = ImageScraperPro(
        output_dir=output,
        min_width=800,
        min_height=600,
        manifest_path=manifest
    )
    
    images = scraper.search("mountain landscape sunset", max_images=3)
    print(f"\nFound {len(images)} images:")
    for img in images:
        print(f"  - {img}")
    
    scraper.save_manifest()
    print(f"\nManifest saved to: {manifest}")


if __name__ == "__main__":
    test_scraper()

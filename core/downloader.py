"""
Da Editor - Video Downloader (v2)
===================================
FIXED:
- Retry logic with exponential backoff for 403 and network errors
- Better filename sanitization to avoid path issues
- Multiple user agents to avoid blocks
- Timeout handling
"""

import os
import re
import time
import random
from typing import Callable, Optional


class VideoDownloader:
    """
    download videos using yt-dlp with retry logic
    supports youtube, tiktok, instagram, twitter, and more
    
    v2 FIXES:
    - Retry with backoff for 403/network errors
    - Better error handling
    - Sanitized filenames
    """
    
    # User agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    
    def __init__(
        self,
        output_dir: str,
        on_progress: Callable[[str], None] = None,
        max_retries: int = 3
    ):
        self.output_dir = output_dir
        self.on_progress = on_progress or (lambda x: None)
        self.max_retries = max_retries
        
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"[Downloader v2] ready - output: {output_dir}")
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize filename to avoid issues with special characters"""
        if not title:
            return "video"
        
        # Remove or replace problematic characters
        # Keep alphanumeric, spaces, hyphens, underscores
        sanitized = re.sub(r'[^\w\s\-]', '', title)
        # Replace multiple spaces/underscores with single underscore
        sanitized = re.sub(r'[\s_]+', '_', sanitized)
        # Limit length
        sanitized = sanitized[:80]
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        
        return sanitized or "video"
    
    def download(self, url: str) -> Optional[str]:
        """
        Download a single video from url with retry logic
        Returns path to downloaded file or None if failed
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = self._download_attempt(url, attempt)
                if result:
                    return result
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check if it's a retryable error
                is_retryable = any(x in error_str for x in [
                    '403', '429', '503', 'timeout', 'connection', 
                    'network', 'temporary', 'unavailable'
                ])
                
                if is_retryable and attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    self.on_progress(f"Retry {attempt + 1}/{self.max_retries} in {delay:.1f}s: {str(e)[:50]}...")
                    time.sleep(delay)
                else:
                    break
        
        if last_error:
            print(f"[Downloader] failed after {self.max_retries} attempts: {last_error}")
        
        return None
    
    def _download_attempt(self, url: str, attempt: int = 0) -> Optional[str]:
        """Single download attempt"""
        try:
            import yt_dlp
        except ImportError:
            print("[Downloader] yt-dlp not installed! run: pip install yt-dlp")
            return None
        
        # Use different user agent on retries
        user_agent = self.USER_AGENTS[attempt % len(self.USER_AGENTS)]
        
        # Get sanitized filename
        output_template = os.path.join(self.output_dir, "%(title).80s.%(ext)s")
        
        ydl_opts = {
            # format selection - get best mp4
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_template,
            # merge to mp4
            "merge_output_format": "mp4",
            # quiet mode but we use hooks for progress
            "quiet": True,
            "no_warnings": True,
            # progress hooks
            "progress_hooks": [self._progress_hook],
            # postprocessor hooks
            "postprocessor_hooks": [self._postprocess_hook],
            # other options
            "ignoreerrors": False,
            "noplaylist": True,
            "extract_flat": False,
            # Retry options
            "retries": 3,
            "fragment_retries": 3,
            "skip_unavailable_fragments": True,
            # Network options
            "socket_timeout": 30,
            # User agent
            "http_headers": {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-us,en;q=0.5",
            },
            # Extractor args for different platforms
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"],
                },
                "tiktok": {
                    "api_hostname": "api16-normal-c-useast1a.tiktokv.com",
                },
            },
        }
        
        # For TikTok, add special options
        if "tiktok.com" in url.lower():
            ydl_opts["format"] = "best"  # TikTok usually has single format
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if info:
                    # Sanitize the title for filename lookup
                    title = self._sanitize_filename(info.get("title", "video"))
                    
                    # Try to find the downloaded file
                    filename = ydl.prepare_filename(info)
                    base = os.path.splitext(filename)[0]
                    
                    for ext in [".mp4", ".webm", ".mkv", ".m4a"]:
                        path = base + ext
                        if os.path.exists(path):
                            # Rename to sanitized filename if needed
                            final_path = self._ensure_safe_path(path)
                            print(f"[Downloader] saved: {final_path}")
                            return final_path
                    
                    # Try finding by sanitized title
                    for ext in [".mp4", ".webm", ".mkv"]:
                        possible_path = os.path.join(self.output_dir, title + ext)
                        if os.path.exists(possible_path):
                            return possible_path
                    
                    # Last resort: find most recent file
                    recent = self._find_most_recent_video()
                    if recent:
                        return recent
                    
                    print(f"[Downloader] warning: couldn't find downloaded file")
                    return None
                    
        except Exception as e:
            # Re-raise to trigger retry
            raise RuntimeError(f"Download failed: {e}")
        
        return None
    
    def _ensure_safe_path(self, path: str) -> str:
        """Rename file to safe path if current path has issues"""
        if not os.path.exists(path):
            return path
        
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)
        name, ext = os.path.splitext(basename)
        
        # Check if name has problematic characters
        safe_name = self._sanitize_filename(name)
        if safe_name != name:
            new_path = os.path.join(dirname, safe_name + ext)
            if not os.path.exists(new_path):
                try:
                    os.rename(path, new_path)
                    return new_path
                except:
                    pass
        
        return path
    
    def _find_most_recent_video(self) -> Optional[str]:
        """Find the most recently created video file in output dir"""
        videos = []
        for f in os.listdir(self.output_dir):
            if f.endswith(('.mp4', '.webm', '.mkv')):
                path = os.path.join(self.output_dir, f)
                mtime = os.path.getmtime(path)
                videos.append((path, mtime))
        
        if videos:
            # Sort by modification time, newest first
            videos.sort(key=lambda x: x[1], reverse=True)
            return videos[0][0]
        
        return None
    
    def _progress_hook(self, d):
        """Called by yt-dlp during download"""
        status = d.get("status")
        
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            
            if total > 0:
                percent = (downloaded / total) * 100
                speed = d.get("speed", 0)
                if speed:
                    speed_mb = speed / (1024 * 1024)
                    self.on_progress(f"Downloading: {percent:.1f}% ({speed_mb:.1f} MB/s)")
                else:
                    self.on_progress(f"Downloading: {percent:.1f}%")
        
        elif status == "finished":
            self.on_progress("Download complete, processing...")
    
    def _postprocess_hook(self, d):
        """Called after download when postprocessing"""
        status = d.get("status")
        if status == "started":
            self.on_progress("Processing video...")
        elif status == "finished":
            self.on_progress("Processing complete")
    
    def get_info(self, url: str) -> Optional[dict]:
        """Get video info without downloading"""
        try:
            import yt_dlp
        except ImportError:
            return None
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 15,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader"),
                    "platform": info.get("extractor_key"),
                    "thumbnail": info.get("thumbnail"),
                }
        except Exception as e:
            print(f"[Downloader] info extraction failed: {e}")
            return None


def test_downloader():
    """quick test to make sure yt-dlp is working"""
    import tempfile
    
    dl = VideoDownloader(
        output_dir=tempfile.mkdtemp(),
        on_progress=lambda x: print(f"  {x}")
    )
    
    # get info for a short video
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    info = dl.get_info(url)
    
    if info:
        print(f"[Test] Title: {info['title']}")
        print(f"[Test] Duration: {info['duration']}s")
        print("[Test] yt-dlp is working!")
    else:
        print("[Test] Failed to get video info")


if __name__ == "__main__":
    test_downloader()

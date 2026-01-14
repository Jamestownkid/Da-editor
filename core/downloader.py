"""
Da Editor - Video Downloader
=============================
1a. uses yt-dlp to grab videos from youtube, tiktok, ig, etc
1b. handles progress callbacks
1c. saves to specified output directory
"""

import os
import re
from typing import Callable, Optional


class VideoDownloader:
    """
    download videos using yt-dlp
    supports youtube, tiktok, instagram, twitter, and more
    
    1a. handles all the yt-dlp config
    1b. reports progress
    1c. returns path to downloaded file
    """
    
    def __init__(
        self,
        output_dir: str,
        on_progress: Callable[[str], None] = None
    ):
        self.output_dir = output_dir
        self.on_progress = on_progress or (lambda x: None)
        
        # make sure dir exists
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"[Downloader] ready - output: {output_dir}")
    
    def download(self, url: str) -> Optional[str]:
        """
        download a single video from url
        returns path to downloaded file or None if failed
        """
        try:
            import yt_dlp
        except ImportError:
            print("[Downloader] yt-dlp not installed! run: pip install yt-dlp")
            return None
        
        # 1a. set up yt-dlp options
        output_template = os.path.join(self.output_dir, "%(title)s.%(ext)s")
        
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
            "noplaylist": True,  # just single videos
            "extract_flat": False,
        }
        
        # 1b. run the download
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if info:
                    # figure out the actual filename
                    filename = ydl.prepare_filename(info)
                    # might have different extension after merge
                    base = os.path.splitext(filename)[0]
                    for ext in [".mp4", ".webm", ".mkv", ".m4a"]:
                        path = base + ext
                        if os.path.exists(path):
                            print(f"[Downloader] saved: {path}")
                            return path
                    
                    # fallback - check if original exists
                    if os.path.exists(filename):
                        return filename
                    
                    print(f"[Downloader] warning: couldn't find downloaded file")
                    return None
                
        except Exception as e:
            print(f"[Downloader] failed: {e}")
            return None
        
        return None
    
    def _progress_hook(self, d):
        """
        2a. called by yt-dlp during download
        reports progress to callback
        """
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
        """
        2b. called after download when postprocessing
        """
        status = d.get("status")
        if status == "started":
            self.on_progress("Processing video...")
        elif status == "finished":
            self.on_progress("Processing complete")
    
    def get_info(self, url: str) -> Optional[dict]:
        """
        3a. get video info without downloading
        useful for checking title, duration, etc
        """
        try:
            import yt_dlp
        except ImportError:
            return None
        
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
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

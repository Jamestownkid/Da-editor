#!/usr/bin/env python3
"""
Da Editor - Job Runner (v4)
============================
FIXED:
- Job time cap (45 minutes max) - no job runs forever
- "no images available" error - fallback to other job folders
- 403 download errors - retry logic with exponential backoff
- Face overlay support for beta feature
- Better error recovery and fault tolerance
"""

import os
import sys
import json
import argparse
import time
import traceback
import signal
import glob
from datetime import datetime
from typing import Dict, List, Optional
from functools import wraps
import random

# make sure we can import our modules
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CORE_DIR)
sys.path.insert(0, ROOT_DIR)

from core.downloader import VideoDownloader
from core.transcriber import WhisperTranscriber
from core.keyword_extractor import KeywordExtractor
from core.image_scraper_pro import ImageScraperPro
from core.video_creator_pro import VideoCreatorPro
from core.safety_monitor import SafetyMonitor


# Job timeout exception
class JobTimeoutError(Exception):
    pass


def log(msg: str):
    """print with timestamp so electron can parse it"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def error(msg: str):
    """print error to stderr and save to file"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] ERROR: {msg}", file=sys.stderr, flush=True)


def retry_with_backoff(max_retries: int = 3, base_delay: float = 2.0, max_delay: float = 30.0):
    """Decorator for retry with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        break
                    
                    # Calculate delay with exponential backoff + jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    total_delay = delay + jitter
                    
                    error_str = str(e)
                    # Only retry on network-related errors
                    if '403' in error_str or '404' in error_str or 'timeout' in error_str.lower() or 'connection' in error_str.lower():
                        log(f"  retry {attempt + 1}/{max_retries} in {total_delay:.1f}s: {error_str[:50]}...")
                        time.sleep(total_delay)
                    else:
                        # Non-retryable error
                        raise
            
            raise last_exception
        
        return wrapper
    return decorator


class JobRunner:
    """
    runs a single job from start to finish
    
    v4 FIXES:
    - 45 minute hard cap per job
    - fallback to other job folders for images
    - retry logic for 403 errors
    - face overlay support
    """
    
    # HARD TIME LIMITS
    MAX_JOB_TIME = 45 * 60  # 45 minutes
    MAX_STEP_TIME = 15 * 60  # 15 minutes per step
    MAX_DOWNLOAD_TIME = 10 * 60  # 10 minutes for downloads
    MAX_SCRAPE_TIME = 10 * 60  # 10 minutes for image scraping
    MAX_RENDER_TIME = 20 * 60  # 20 minutes for rendering
    
    def __init__(self, job_folder: str, settings: dict):
        self.job_folder = job_folder
        self.settings = settings
        self.job_json_path = os.path.join(job_folder, "job.json")
        self.links_path = os.path.join(job_folder, "links.txt")
        self.error_log_path = os.path.join(job_folder, "errors.log")
        
        # Time tracking
        self.job_start_time = time.time()
        self.step_start_time = None
        
        # load existing job data
        self.job = self._load_job()
        
        # folder structure
        self.images_dir = os.path.join(job_folder, "images")
        os.makedirs(self.images_dir, exist_ok=True)
        
        # image manifest for deduplication
        self.image_manifest_path = os.path.join(job_folder, "image_manifest.json")
        
        # global manifest in output root for cross-job deduplication
        output_folder = settings.get("outputFolder", "")
        self.global_manifest_path = os.path.join(output_folder, "global_image_manifest.json") if output_folder else None
        self.output_folder = output_folder
        
        # safety monitor
        self.monitor = SafetyMonitor()
        
        # timeout handling
        self._setup_timeout_handler()
        
        log(f"job runner v4 initialized: {job_folder}")
        log(f"  max job time: {self.MAX_JOB_TIME // 60} minutes")
    
    def _setup_timeout_handler(self):
        """Setup signal handler for job timeout"""
        def timeout_handler(signum, frame):
            raise JobTimeoutError(f"Job exceeded {self.MAX_JOB_TIME // 60} minute limit")
        
        # Set up alarm signal (Unix only)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.MAX_JOB_TIME)
    
    def _check_time_limit(self, step_name: str, max_time: int = None):
        """Check if we've exceeded time limits"""
        elapsed = time.time() - self.job_start_time
        
        if elapsed > self.MAX_JOB_TIME:
            raise JobTimeoutError(f"Job exceeded {self.MAX_JOB_TIME // 60} minute limit during {step_name}")
        
        if self.step_start_time and max_time:
            step_elapsed = time.time() - self.step_start_time
            if step_elapsed > max_time:
                log(f"WARNING: {step_name} exceeded {max_time // 60} minute limit, moving on...")
                return False
        
        return True
    
    def _load_job(self) -> dict:
        """load job data from json"""
        if os.path.exists(self.job_json_path):
            try:
                with open(self.job_json_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                error(f"failed to load job.json: {e}")
        return {"urls": [], "status": "pending", "created": datetime.now().isoformat()}
    
    def _save_job(self):
        """save current job state"""
        self.job["last_updated"] = datetime.now().isoformat()
        self.job["jobFolder"] = self.job_folder
        with open(self.job_json_path, "w") as f:
            json.dump(self.job, f, indent=2)
    
    def _log_error(self, msg: str):
        """log error to file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.error_log_path, "a") as f:
            f.write(f"[{timestamp}] {msg}\n")
        error(msg)
    
    def _save_links_txt(self):
        """save links.txt with [SRT][IMG] markers"""
        lines = []
        for url_data in self.job.get("urls", []):
            url = url_data.get("url", "")
            markers = ""
            if url_data.get("srt"):
                markers += " [SRT]"
            if url_data.get("images"):
                markers += "[IMG]"
            lines.append(f"{url}{markers}")
        
        with open(self.links_path, "w") as f:
            f.write("\n".join(lines) + "\n")
    
    def run(self):
        """main entry - runs the whole pipeline with time limits"""
        try:
            # safety check first
            log("checking system resources...")
            status = self.monitor.check()
            if not status["safe"]:
                self._log_error(f"system not safe to run: {status}")
                return False
            
            # save links.txt
            self._save_links_txt()
            
            # mark as running
            self.job["status"] = "running"
            self._save_job()
            
            # step 1: download all videos
            log("step 1: downloading videos...")
            self.step_start_time = time.time()
            self._download_videos()
            
            # step 2: generate SRT for marked links
            log("step 2: generating SRT files...")
            self.step_start_time = time.time()
            self._generate_srt()
            
            # step 3: extract keywords from SRT
            log("step 3: extracting keywords...")
            self.step_start_time = time.time()
            keywords = self._extract_keywords()
            
            # step 4: scrape images with fallback
            log("step 4: scraping images...")
            self.step_start_time = time.time()
            self._scrape_images_with_fallback(keywords)
            
            # step 5: create video outputs
            log("step 5: creating video outputs...")
            self.step_start_time = time.time()
            self._create_outputs()
            
            # step 6: validate outputs
            log("step 6: validating outputs...")
            self._validate_outputs()
            
            # mark as done
            self.job["status"] = "done"
            self._save_job()
            
            # Cancel alarm
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            elapsed = time.time() - self.job_start_time
            log(f"job completed in {elapsed / 60:.1f} minutes!")
            return True
            
        except JobTimeoutError as e:
            self._log_error(f"TIMEOUT: {e}")
            self.job["status"] = "error"
            self.job["errors"] = self.job.get("errors", []) + [str(e)]
            self._save_job()
            return False
            
        except Exception as e:
            self._log_error(f"job failed: {e}")
            traceback.print_exc(file=sys.stderr)
            self.job["status"] = "error"
            self._save_job()
            return False
    
    def _download_videos(self):
        """download all videos from urls with retry logic"""
        downloader = VideoDownloader(
            output_dir=self.job_folder,
            on_progress=log
        )
        
        urls = self.job.get("urls", [])
        downloaded = []
        failed_urls = []
        
        for i, url_data in enumerate(urls):
            # Check time limit
            if not self._check_time_limit("download", self.MAX_DOWNLOAD_TIME):
                log("download time limit reached, continuing with what we have...")
                break
            
            url = url_data.get("url", "")
            if not url:
                continue
            
            # check if already downloaded
            existing = url_data.get("downloaded_path")
            if existing and os.path.exists(existing):
                log(f"already downloaded: {os.path.basename(existing)}")
                downloaded.append(url_data)
                continue
            
            log(f"downloading [{i+1}/{len(urls)}]: {url[:60]}...")
            
            # throttle
            time.sleep(0.5)
            
            try:
                path = self._download_with_retry(downloader, url)
                if path:
                    url_data["downloaded_path"] = path
                    url_data["platform"] = self._detect_platform(url)
                    downloaded.append(url_data)
                    log(f"  saved: {os.path.basename(path)}")
                else:
                    failed_urls.append(url)
            except Exception as e:
                self._log_error(f"download failed for {url}: {e}")
                failed_urls.append(url)
                # Continue with other URLs instead of failing completely
                continue
        
        if failed_urls:
            log(f"WARNING: {len(failed_urls)} downloads failed, continuing with {len(downloaded)} videos")
        
        self._save_job()
        log(f"downloaded {len(downloaded)} videos")
    
    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def _download_with_retry(self, downloader, url: str) -> Optional[str]:
        """Download with retry logic for 403 and other errors"""
        return downloader.download(url)
    
    def _detect_platform(self, url: str) -> str:
        """detect platform from url"""
        url_lower = url.lower()
        if "tiktok.com" in url_lower:
            return "tiktok"
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        elif "instagram.com" in url_lower:
            return "instagram"
        return "other"
    
    def _generate_srt(self):
        """generate SRT for urls marked with srt=true"""
        srt_urls = [u for u in self.job.get("urls", []) if u.get("srt")]
        
        if not srt_urls:
            log("no urls marked for SRT generation")
            return
        
        model = self.settings.get("whisperModel", "medium")
        use_gpu = self.settings.get("useGpu", True)
        
        log(f"using whisper model: {model}, gpu: {use_gpu}")
        
        transcriber = WhisperTranscriber(
            model_name=model,
            use_gpu=use_gpu,
            output_dir=self.job_folder
        )
        
        for url_data in srt_urls:
            # Check time limit
            if not self._check_time_limit("transcription", self.MAX_STEP_TIME):
                log("transcription time limit reached, continuing...")
                break
            
            video_path = url_data.get("downloaded_path")
            if not video_path or not os.path.exists(video_path):
                self._log_error(f"video not found for SRT: {url_data.get('url')}")
                continue
            
            existing_srt = url_data.get("srt_path")
            if existing_srt and os.path.exists(existing_srt):
                log(f"SRT already exists: {os.path.basename(existing_srt)}")
                continue
            
            log(f"transcribing: {os.path.basename(video_path)}...")
            
            try:
                srt_path = transcriber.transcribe(video_path)
                if srt_path:
                    url_data["srt_path"] = srt_path
                    log(f"  SRT saved: {os.path.basename(srt_path)}")
            except Exception as e:
                self._log_error(f"transcription failed: {e}")
                # Continue with other videos
                continue
        
        self._save_job()
    
    def _extract_keywords(self) -> List[str]:
        """extract keywords from SRT files"""
        extractor = KeywordExtractor()
        all_keywords = []
        
        for url_data in self.job.get("urls", []):
            srt_path = url_data.get("srt_path")
            if not srt_path or not os.path.exists(srt_path):
                continue
            
            log(f"extracting keywords from: {os.path.basename(srt_path)}")
            keywords = extractor.extract_from_srt(srt_path, max_keywords=30)
            all_keywords.extend(keywords)
        
        unique = list(dict.fromkeys(all_keywords))[:40]
        self.job["keywords"] = unique
        self._save_job()
        
        log(f"extracted {len(unique)} keywords")
        return unique
    
    def _scrape_images_with_fallback(self, keywords: List[str]):
        """
        Scrape images with fallback to other job folders
        This is the FIX for "no images available for rendering"
        """
        img_urls = [u for u in self.job.get("urls", []) if u.get("images")]
        
        if not img_urls:
            log("no urls marked for image scraping")
        
        min_images = self.settings.get("minImages", 15)
        
        # First: try to scrape new images
        if keywords and img_urls:
            self._scrape_images(keywords, min_images)
        
        # Check how many images we have
        current_images = [img for img in self.job.get("images", []) if os.path.exists(img)]
        
        # FALLBACK: if not enough images, borrow from other job folders
        if len(current_images) < min_images:
            log(f"only {len(current_images)} images, looking for fallback sources...")
            self._borrow_images_from_other_jobs(min_images - len(current_images))
        
        # Final check
        final_images = [img for img in self.job.get("images", []) if os.path.exists(img)]
        if len(final_images) == 0:
            self._log_error("no images available even after fallback - using placeholder")
            # Create a simple placeholder image as last resort
            self._create_placeholder_image()
    
    def _scrape_images(self, keywords: List[str], min_images: int):
        """Normal image scraping with time limit"""
        scraper = ImageScraperPro(
            output_dir=self.images_dir,
            min_width=900,
            min_height=700,
            min_size_kb=50,
            manifest_path=self.global_manifest_path
        )
        
        images = []
        scrape_start = time.time()
        
        for keyword in keywords:
            # Check time limit
            if time.time() - scrape_start > self.MAX_SCRAPE_TIME:
                log("image scraping time limit reached, using what we have...")
                break
            
            if len(images) >= min_images:
                break
            
            log(f"searching: {keyword}")
            
            time.sleep(1.0)
            
            status = self.monitor.check()
            if status.get("cpu") == "HIGH":
                log("cpu high, waiting 5s...")
                time.sleep(5.0)
            
            try:
                found = scraper.search(keyword, max_images=3)
                images.extend(found)
            except Exception as e:
                self._log_error(f"scrape failed for '{keyword}': {e}")
                continue
        
        scraper.save_manifest()
        
        self.job["images"] = images
        self._save_job()
        
        log(f"scraped {len(images)} images")
    
    def _borrow_images_from_other_jobs(self, needed: int):
        """
        FALLBACK: Borrow images from other job folders
        This ensures we always have images for rendering
        """
        if not self.output_folder or not os.path.isdir(self.output_folder):
            return
        
        borrowed = []
        current_images = set(self.job.get("images", []))
        
        # Find other job folders
        for folder_name in os.listdir(self.output_folder):
            if len(borrowed) >= needed:
                break
            
            folder_path = os.path.join(self.output_folder, folder_name)
            if not os.path.isdir(folder_path):
                continue
            
            # Skip current job folder
            if os.path.samefile(folder_path, self.job_folder):
                continue
            
            # Look for images subfolder
            other_images_dir = os.path.join(folder_path, "images")
            if not os.path.isdir(other_images_dir):
                continue
            
            # Get images from this folder
            for img_file in os.listdir(other_images_dir):
                if len(borrowed) >= needed:
                    break
                
                if not img_file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    continue
                
                source_path = os.path.join(other_images_dir, img_file)
                
                # Copy to our images folder
                dest_name = f"fallback_{folder_name}_{img_file}"
                dest_path = os.path.join(self.images_dir, dest_name)
                
                if dest_path in current_images:
                    continue
                
                try:
                    import shutil
                    shutil.copy2(source_path, dest_path)
                    borrowed.append(dest_path)
                    log(f"  borrowed: {dest_name}")
                except Exception as e:
                    continue
        
        if borrowed:
            log(f"borrowed {len(borrowed)} images from other jobs")
            self.job["images"] = list(current_images) + borrowed
            self._save_job()
    
    def _create_placeholder_image(self):
        """Create a simple placeholder image as absolute last resort"""
        try:
            from PIL import Image, ImageDraw
            
            # Create a simple gradient image
            img = Image.new('RGB', (1920, 1080), color=(30, 30, 40))
            draw = ImageDraw.Draw(img)
            
            # Add some text
            draw.text((960, 540), "B-Roll", fill=(100, 100, 120), anchor="mm")
            
            placeholder_path = os.path.join(self.images_dir, "_placeholder.png")
            img.save(placeholder_path)
            
            self.job["images"] = [placeholder_path]
            self._save_job()
            log("created placeholder image")
            
        except Exception as e:
            self._log_error(f"could not create placeholder: {e}")
    
    def _create_outputs(self):
        """Create video outputs with face overlay support"""
        images = self.job.get("images", [])
        images = [img for img in images if os.path.exists(img)]
        
        if not images:
            self._log_error("no images available for rendering")
            return
        
        # Convert palette images to RGBA to avoid PIL warning
        images = self._convert_palette_images(images)
        
        sounds_dir = self.settings.get("soundsFolder", "")
        if not sounds_dir:
            sounds_dir = os.path.join(ROOT_DIR, "assets", "sounds")
        
        srt_duration = self._get_srt_duration()
        face_overlay_path = self.settings.get("faceOverlayPath")
        
        creator = VideoCreatorPro(
            images_dir=self.images_dir,
            videos_dir=self.job_folder,
            output_dir=self.job_folder,
            sounds_dir=sounds_dir,
            settings={
                **self.settings,
                "targetDuration": srt_duration,
                "faceOverlayPath": face_overlay_path
            }
        )
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outputs = {}
        
        # output 1: landscape b-roll
        log("creating output_video.mp4 (landscape b-roll)...")
        try:
            if not self._check_time_limit("render", self.MAX_RENDER_TIME):
                log("render time limit reached, skipping remaining outputs...")
            else:
                output1 = creator.create_slideshow(images, "output_video.mp4")
                if output1:
                    outputs["slideshow"] = output1
                    log(f"  done: output_video.mp4")
        except Exception as e:
            self._log_error(f"landscape b-roll failed: {e}")
            traceback.print_exc(file=sys.stderr)
        
        # output 2: portrait/instagram
        log("creating broll_instagram (portrait)...")
        try:
            if self._check_time_limit("render", self.MAX_RENDER_TIME):
                output2 = creator.create_portrait(images, f"broll_instagram_{timestamp}.mp4")
                if output2:
                    outputs["portrait"] = output2
                    log(f"  done: broll_instagram_{timestamp}.mp4")
        except Exception as e:
            self._log_error(f"portrait failed: {e}")
            traceback.print_exc(file=sys.stderr)
        
        # output 3: youtube mix
        youtube_vids = [
            u.get("downloaded_path") for u in self.job.get("urls", [])
            if u.get("platform") == "youtube" and u.get("downloaded_path")
            and os.path.exists(u.get("downloaded_path", ""))
        ]
        
        if youtube_vids and self._check_time_limit("render", self.MAX_RENDER_TIME):
            log("creating broll_youtube (youtube mix)...")
            try:
                output3 = creator.create_youtube_mix(youtube_vids, f"broll_youtube_{timestamp}.mp4")
                if output3:
                    outputs["youtubeMix"] = output3
                    log(f"  done: broll_youtube_{timestamp}.mp4")
            except Exception as e:
                self._log_error(f"youtube mix failed: {e}")
                traceback.print_exc(file=sys.stderr)
        else:
            log("no youtube videos for output #3 (youtube mix)")
        
        self.job["outputs"] = outputs
        self._save_job()
    
    def _convert_palette_images(self, images: List[str]) -> List[str]:
        """Convert palette images to RGBA to avoid PIL warnings"""
        converted = []
        
        try:
            from PIL import Image
            
            for img_path in images:
                try:
                    with Image.open(img_path) as img:
                        if img.mode == 'P':
                            # Convert palette image with transparency to RGBA
                            rgba_img = img.convert('RGBA')
                            new_path = img_path.rsplit('.', 1)[0] + '_converted.png'
                            rgba_img.save(new_path)
                            converted.append(new_path)
                            log(f"converted palette image: {os.path.basename(img_path)}")
                        else:
                            converted.append(img_path)
                except Exception as e:
                    # Keep original if conversion fails
                    converted.append(img_path)
        except ImportError:
            return images
        
        return converted
    
    def _validate_outputs(self):
        """validate that outputs are actually playable"""
        outputs = self.job.get("outputs", {})
        valid = {}
        
        for name, path in outputs.items():
            if not path or not os.path.exists(path):
                log(f"  {name}: missing")
                continue
            
            size = os.path.getsize(path)
            if size < 10000:
                log(f"  {name}: too small ({size} bytes)")
                continue
            
            try:
                import subprocess
                result = subprocess.run([
                    "ffprobe", "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=codec_name,duration",
                    "-of", "json",
                    path
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    info = json.loads(result.stdout)
                    if info.get("streams"):
                        valid[name] = path
                        size_mb = size / (1024 * 1024)
                        log(f"  {name}: OK ({size_mb:.1f}MB)")
                        continue
            except Exception as e:
                pass
            
            log(f"  {name}: validation failed")
        
        self.job["valid_outputs"] = valid
        self._save_job()
        
        log(f"validated {len(valid)}/{len(outputs)} outputs")
    
    def _get_srt_duration(self) -> float:
        """get duration from SRT file for output matching"""
        for url_data in self.job.get("urls", []):
            srt_path = url_data.get("srt_path")
            if srt_path and os.path.exists(srt_path):
                try:
                    with open(srt_path, "r") as f:
                        content = f.read()
                    
                    import re
                    timestamps = re.findall(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', content)
                    if timestamps:
                        last = timestamps[-1]
                        seconds = int(last[0]) * 3600 + int(last[1]) * 60 + int(last[2])
                        return float(seconds)
                except:
                    pass
        
        return 60.0
    
    def delete_videos_after_use(self):
        """delete downloaded videos to save space"""
        if not self.settings.get("deleteAfterUse"):
            return
        
        for url_data in self.job.get("urls", []):
            video_path = url_data.get("downloaded_path")
            if video_path and os.path.exists(video_path):
                try:
                    os.unlink(video_path)
                    log(f"deleted: {os.path.basename(video_path)}")
                    url_data["deleted"] = True
                except Exception as e:
                    self._log_error(f"failed to delete {video_path}: {e}")
        
        self._save_job()


def main():
    parser = argparse.ArgumentParser(description="Da Editor Job Runner v4")
    parser.add_argument("--job-folder", required=True, help="Path to job folder")
    parser.add_argument("--settings", required=True, help="JSON string of settings")
    
    args = parser.parse_args()
    
    try:
        settings = json.loads(args.settings)
    except json.JSONDecodeError:
        error("invalid settings JSON")
        sys.exit(1)
    
    runner = JobRunner(args.job_folder, settings)
    success = runner.run()
    
    if success and settings.get("deleteAfterUse"):
        runner.delete_videos_after_use()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

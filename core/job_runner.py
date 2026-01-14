#!/usr/bin/env python3
"""
Da Editor - Job Runner (v2)
============================
this the upgraded version that matches the expected output structure
runs the whole pipeline from download to render

handles per-link SRT and image toggles like the real deal
"""

import os
import sys
import json
import argparse
import time
import traceback
import threading
from datetime import datetime
from typing import Dict, List, Optional

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


def log(msg: str):
    """print with timestamp so electron can parse it"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def error(msg: str):
    """print error to stderr and save to file"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] ERROR: {msg}", file=sys.stderr, flush=True)


class JobRunner:
    """
    runs a single job from start to finish
    
    per spec rules 5, 60, 69-72, 87-92:
    - per-link SRT and image toggles
    - errors saved to disk (rule 60)
    - delete after use option (rule 69)
    - image manifest tracking (rule 88)
    - throttled scraping (rule 92)
    """
    
    def __init__(self, job_folder: str, settings: dict):
        self.job_folder = job_folder
        self.settings = settings
        self.job_json_path = os.path.join(job_folder, "job.json")
        self.links_path = os.path.join(job_folder, "links.txt")
        self.error_log_path = os.path.join(job_folder, "errors.log")
        
        # load existing job data
        self.job = self._load_job()
        
        # create folder structure matching sample
        # videos go directly in job folder (downloads)
        # images in images/ subfolder
        # outputs: broll_instagram, broll_youtube, output_video
        self.images_dir = os.path.join(job_folder, "images")
        os.makedirs(self.images_dir, exist_ok=True)
        
        # image manifest for deduplication (rules 87-90)
        self.image_manifest_path = os.path.join(job_folder, "image_manifest.json")
        self.image_manifest = self._load_image_manifest()
        
        # safety monitor
        self.monitor = SafetyMonitor()
        
        log(f"job runner v2 initialized: {job_folder}")
    
    def _load_job(self) -> dict:
        """load job data from json"""
        if os.path.exists(self.job_json_path):
            with open(self.job_json_path, "r") as f:
                return json.load(f)
        return {"urls": [], "status": "pending"}
    
    def _save_job(self):
        """save current job state"""
        self.job["last_updated"] = datetime.now().isoformat()
        with open(self.job_json_path, "w") as f:
            json.dump(self.job, f, indent=2)
    
    def _log_error(self, msg: str):
        """log error to file (rule 60)"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.error_log_path, "a") as f:
            f.write(f"[{timestamp}] {msg}\n")
        error(msg)
    
    def _load_image_manifest(self) -> dict:
        """load image manifest for deduplication (rule 88)"""
        if os.path.exists(self.image_manifest_path):
            try:
                with open(self.image_manifest_path, "r") as f:
                    return json.load(f)
            except:
                pass
        return {"used_hashes": [], "used_urls": [], "images": []}
    
    def _save_image_manifest(self):
        """save image manifest"""
        with open(self.image_manifest_path, "w") as f:
            json.dump(self.image_manifest, f, indent=2)
    
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
        """main entry - runs the whole pipeline"""
        try:
            # safety check first - dont crush the cpu (rules 64-65)
            log("checking system resources...")
            status = self.monitor.check()
            if not status["safe"]:
                self._log_error(f"system not safe to run: {status}")
                return False
            
            # save links.txt
            self._save_links_txt()
            
            # step 1: download all videos
            log("step 1: downloading videos...")
            self._download_videos()
            
            # step 2: generate SRT for marked links (rule 5)
            log("step 2: generating SRT files...")
            self._generate_srt()
            
            # step 3: extract keywords from SRT
            log("step 3: extracting keywords...")
            keywords = self._extract_keywords()
            
            # step 4: scrape images in background (rules 8, 91-92)
            log("step 4: scraping images (background)...")
            self._scrape_images(keywords)
            
            # step 5: create video outputs
            log("step 5: creating video outputs...")
            self._create_outputs()
            
            # mark as done
            self.job["status"] = "done"
            self._save_job()
            log("job completed!")
            return True
            
        except Exception as e:
            self._log_error(f"job failed: {e}")
            traceback.print_exc(file=sys.stderr)
            self.job["status"] = "error"
            self._save_job()
            return False
    
    def _download_videos(self):
        """download all videos from urls"""
        downloader = VideoDownloader(
            output_dir=self.job_folder,  # download directly to job folder
            on_progress=log
        )
        
        urls = self.job.get("urls", [])
        downloaded = []
        
        for i, url_data in enumerate(urls):
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
            
            # throttle to not kill cpu (rule 92)
            time.sleep(0.5)
            
            try:
                path = downloader.download(url)
                if path:
                    url_data["downloaded_path"] = path
                    url_data["platform"] = self._detect_platform(url)
                    downloaded.append(url_data)
                    log(f"  saved: {os.path.basename(path)}")
            except Exception as e:
                self._log_error(f"download failed for {url}: {e}")
        
        self._save_job()
        log(f"downloaded {len(downloaded)} videos")
    
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
        """generate SRT for urls marked with srt=true (rule 5)"""
        # find urls that need SRT
        srt_urls = [u for u in self.job.get("urls", []) if u.get("srt")]
        
        if not srt_urls:
            log("no urls marked for SRT generation")
            return
        
        # init whisper with settings
        model = self.settings.get("whisperModel", "medium")
        use_gpu = self.settings.get("useGpu", True)
        
        log(f"using whisper model: {model}, gpu: {use_gpu}")
        
        transcriber = WhisperTranscriber(
            model_name=model,
            use_gpu=use_gpu,
            output_dir=self.job_folder  # SRT goes in job folder root
        )
        
        for url_data in srt_urls:
            video_path = url_data.get("downloaded_path")
            if not video_path or not os.path.exists(video_path):
                self._log_error(f"video not found for SRT: {url_data.get('url')}")
                continue
            
            # check if SRT already exists
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
        
        # dedupe and save
        unique = list(dict.fromkeys(all_keywords))[:40]
        self.job["keywords"] = unique
        self._save_job()
        
        log(f"extracted {len(unique)} keywords")
        return unique
    
    def _scrape_images(self, keywords: List[str]):
        """
        scrape images based on keywords
        runs with throttling to not kill cpu (rules 91-92)
        tracks used images to avoid duplicates (rules 87-90)
        """
        # find urls that need images
        img_urls = [u for u in self.job.get("urls", []) if u.get("images")]
        
        if not img_urls or not keywords:
            log("no urls marked for image scraping or no keywords")
            return
        
        scraper = ImageScraperPro(
            output_dir=self.images_dir,
            min_width=900,  # rule 115
            min_height=700,
            min_size_kb=50
        )
        
        # pass existing manifest hashes to scraper for deduplication
        scraper.used_hashes = set(self.image_manifest.get("used_hashes", []))
        scraper.used_urls = set(self.image_manifest.get("used_urls", []))
        
        min_images = self.settings.get("minImages", 12)
        images = []
        
        for keyword in keywords:
            if len(images) >= min_images:
                break
            
            log(f"searching: {keyword}")
            
            # throttle to be gentle (rule 92)
            time.sleep(1.0)
            
            # check cpu before each search (rule 65)
            status = self.monitor.check()
            if status.get("cpu") == "HIGH":
                log("cpu high, waiting...")
                time.sleep(5.0)
            
            try:
                found = scraper.search(keyword, max_images=3)
                images.extend(found)
            except Exception as e:
                self._log_error(f"scrape failed for '{keyword}': {e}")
        
        # update manifest (rule 88)
        self.image_manifest["used_hashes"] = list(scraper.used_hashes)
        self.image_manifest["used_urls"] = list(scraper.used_urls)
        self.image_manifest["images"] = images
        self._save_image_manifest()
        
        self.job["images"] = images
        self._save_job()
        
        log(f"scraped {len(images)} images")
    
    def _create_outputs(self):
        """
        create the video outputs:
        - output_video.mp4 (landscape b-roll)
        - broll_instagram_*.mp4 (portrait)
        - broll_youtube_*.mp4 (youtube mix)
        
        per rules 34-57
        """
        images = self.job.get("images", [])
        images = [img for img in images if os.path.exists(img)]
        
        if not images:
            self._log_error("no images available for rendering")
            return
        
        # get sounds folder
        sounds_dir = self.settings.get("soundsFolder", "")
        if not sounds_dir:
            sounds_dir = os.path.join(ROOT_DIR, "assets", "sounds")
        
        # get srt duration for output length matching (rule 35)
        srt_duration = self._get_srt_duration()
        
        creator = VideoCreatorPro(
            images_dir=self.images_dir,
            videos_dir=self.job_folder,
            output_dir=self.job_folder,  # outputs go in job folder root
            sounds_dir=sounds_dir,
            settings={
                **self.settings,
                "targetDuration": srt_duration
            }
        )
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # output 1: landscape b-roll (output_video.mp4)
        log("creating output_video.mp4 (landscape b-roll)...")
        try:
            output1 = creator.create_slideshow(images, "output_video.mp4")
            if output1:
                self.job["outputs"] = self.job.get("outputs", {})
                self.job["outputs"]["landscape"] = output1
                log(f"  done: output_video.mp4")
        except Exception as e:
            self._log_error(f"landscape b-roll failed: {e}")
        
        # output 2: portrait/instagram (broll_instagram_*.mp4)
        log("creating broll_instagram (portrait)...")
        try:
            output2 = creator.create_portrait(images, f"broll_instagram_{timestamp}.mp4")
            if output2:
                self.job["outputs"]["portrait"] = output2
                log(f"  done: broll_instagram_{timestamp}.mp4")
        except Exception as e:
            self._log_error(f"portrait failed: {e}")
        
        # output 3: youtube mix (broll_youtube_*.mp4) - only youtube videos
        youtube_vids = [
            u.get("downloaded_path") for u in self.job.get("urls", [])
            if u.get("platform") == "youtube" and u.get("downloaded_path")
            and os.path.exists(u.get("downloaded_path", ""))
        ]
        
        if youtube_vids:
            log("creating broll_youtube (youtube mix)...")
            try:
                output3 = creator.create_youtube_mix(youtube_vids, f"broll_youtube_{timestamp}.mp4")
                if output3:
                    self.job["outputs"]["youtube_mix"] = output3
                    log(f"  done: broll_youtube_{timestamp}.mp4")
            except Exception as e:
                self._log_error(f"youtube mix failed: {e}")
        
        self._save_job()
    
    def _get_srt_duration(self) -> float:
        """get duration from SRT file for output matching (rule 35)"""
        for url_data in self.job.get("urls", []):
            srt_path = url_data.get("srt_path")
            if srt_path and os.path.exists(srt_path):
                try:
                    with open(srt_path, "r") as f:
                        content = f.read()
                    
                    # find last timestamp
                    import re
                    timestamps = re.findall(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', content)
                    if timestamps:
                        last = timestamps[-1]
                        seconds = int(last[0]) * 3600 + int(last[1]) * 60 + int(last[2])
                        return float(seconds)
                except:
                    pass
        
        return 60.0  # default
    
    def delete_videos_after_use(self):
        """delete downloaded videos to save space (rule 69-70)"""
        if not self.settings.get("deleteAfterUse"):
            return
        
        for url_data in self.job.get("urls", []):
            video_path = url_data.get("downloaded_path")
            if video_path and os.path.exists(video_path):
                try:
                    os.unlink(video_path)
                    log(f"deleted: {os.path.basename(video_path)}")
                    # keep the path in json for revert (rule 70)
                    url_data["deleted"] = True
                except Exception as e:
                    self._log_error(f"failed to delete {video_path}: {e}")
        
        self._save_job()
    
    def revert_deleted_videos(self) -> dict:
        """
        show what would be restored and optionally restore (rules 71-72)
        returns dict of what will be downloaded
        """
        to_restore = []
        
        for url_data in self.job.get("urls", []):
            if url_data.get("deleted"):
                to_restore.append({
                    "url": url_data.get("url"),
                    "platform": url_data.get("platform"),
                    "was_path": url_data.get("downloaded_path")
                })
        
        return {"to_restore": to_restore, "count": len(to_restore)}


def main():
    parser = argparse.ArgumentParser(description="Da Editor Job Runner v2")
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
    
    # optionally delete videos after use (rule 69)
    if success and settings.get("deleteAfterUse"):
        runner.delete_videos_after_use()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

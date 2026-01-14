#!/usr/bin/env python3
"""
Da Editor - Job Runner
=======================
this is what gets called from electron to actually process jobs
runs the whole pipeline from download to render

we keeping it resilient - crashes shouldnt lose progress yo
"""

import os
import sys
import json
import argparse
import time
import traceback
from datetime import datetime

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
    """print error to stderr"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] ERROR: {msg}", file=sys.stderr, flush=True)


class JobRunner:
    """
    runs a single job from start to finish
    handles checkpoints so we can resume if something breaks
    
    1a. validates inputs
    1b. runs each step
    1c. saves checkpoints
    1d. creates 3 video outputs
    """
    
    def __init__(self, job_folder: str, settings: dict):
        self.job_folder = job_folder
        self.settings = settings
        self.job_json_path = os.path.join(job_folder, "job.json")
        
        # load existing job data
        self.job = self._load_job()
        
        # set up directories
        self.downloads_dir = os.path.join(job_folder, "downloads")
        self.srt_dir = os.path.join(job_folder, "srt")
        self.images_dir = os.path.join(job_folder, "images")
        self.renders_dir = os.path.join(job_folder, "renders")
        self.logs_dir = os.path.join(job_folder, "logs")
        self.cache_dir = os.path.join(job_folder, "cache")
        
        # make sure all dirs exist
        for d in [self.downloads_dir, self.srt_dir, self.images_dir, 
                  self.renders_dir, self.logs_dir, self.cache_dir]:
            os.makedirs(d, exist_ok=True)
        
        # safety monitor
        self.monitor = SafetyMonitor()
        
        log(f"job runner initialized: {job_folder}")
    
    def _load_job(self) -> dict:
        """load job data from json"""
        if os.path.exists(self.job_json_path):
            with open(self.job_json_path, "r") as f:
                return json.load(f)
        return {}
    
    def _save_job(self):
        """save current job state"""
        self.job["last_updated"] = datetime.now().isoformat()
        with open(self.job_json_path, "w") as f:
            json.dump(self.job, f, indent=2)
    
    def _set_checkpoint(self, checkpoint: str):
        """mark where we at in the pipeline"""
        self.job["checkpoint"] = checkpoint
        self._save_job()
        log(f"checkpoint: {checkpoint}")
    
    def run(self):
        """
        main entry - runs the whole pipeline
        checks for existing progress and resumes from checkpoint
        """
        try:
            # 1a. safety check first
            log("checking system resources...")
            status = self.monitor.check()
            if not status["safe"]:
                error(f"system not safe to run: {status}")
                return False
            
            # 1b. get checkpoint or start fresh
            checkpoint = self.job.get("checkpoint", "start")
            log(f"starting from checkpoint: {checkpoint}")
            
            # run pipeline based on checkpoint
            steps = ["download", "transcribe", "keywords", "scrape", "render", "validate"]
            start_idx = 0
            
            for i, step in enumerate(steps):
                if checkpoint == step or checkpoint == "start":
                    start_idx = i
                    break
            
            # run remaining steps
            for step in steps[start_idx:]:
                # check safety before each step
                status = self.monitor.check()
                if not status["safe"]:
                    error(f"stopping - system resources low: {status}")
                    self._set_checkpoint(step)
                    return False
                
                # run the step
                success = self._run_step(step)
                if not success:
                    error(f"step failed: {step}")
                    return False
            
            # mark as done
            self.job["status"] = "done"
            self.job["progress"] = 100
            self._save_job()
            log("job completed successfully!")
            return True
            
        except Exception as e:
            error(f"job failed: {e}")
            traceback.print_exc(file=sys.stderr)
            self.job["status"] = "error"
            self.job["errors"] = self.job.get("errors", []) + [str(e)]
            self._save_job()
            return False
    
    def _run_step(self, step: str) -> bool:
        """run a single pipeline step"""
        self._set_checkpoint(step)
        
        if step == "download":
            return self._step_download()
        elif step == "transcribe":
            return self._step_transcribe()
        elif step == "keywords":
            return self._step_keywords()
        elif step == "scrape":
            return self._step_scrape()
        elif step == "render":
            return self._step_render()
        elif step == "validate":
            return self._step_validate()
        
        return True
    
    def _step_download(self) -> bool:
        """download all videos from links"""
        if not self.job.get("downloadVideos", True):
            log("skipping downloads (disabled)")
            return True
        
        links = self.job.get("links", [])
        if not links:
            log("no links to download")
            return True
        
        # check what we already got
        downloaded = self.job.get("downloadedVideos", [])
        downloaded_urls = {v.get("url") for v in downloaded}
        
        downloader = VideoDownloader(
            output_dir=self.downloads_dir,
            on_progress=log
        )
        
        for i, link in enumerate(links):
            if link in downloaded_urls:
                log(f"already downloaded: {link[:50]}...")
                continue
            
            log(f"downloading [{i+1}/{len(links)}]: {link[:50]}...")
            
            try:
                path = downloader.download(link)
                if path:
                    # detect platform
                    platform = "other"
                    link_lower = link.lower()
                    if "tiktok.com" in link_lower:
                        platform = "tiktok"
                    elif "youtube.com" in link_lower or "youtu.be" in link_lower:
                        platform = "youtube"
                    elif "instagram.com" in link_lower:
                        platform = "instagram"
                    
                    downloaded.append({
                        "url": link,
                        "path": path,
                        "platform": platform
                    })
                    
            except Exception as e:
                error(f"download failed: {e}")
        
        self.job["downloadedVideos"] = downloaded
        self.job["progress"] = 20
        self._save_job()
        
        log(f"downloaded {len(downloaded)} videos")
        return True
    
    def _step_transcribe(self) -> bool:
        """generate SRT files using whisper"""
        if not self.job.get("generateSrt", True):
            log("skipping transcription (disabled)")
            return True
        
        downloaded = self.job.get("downloadedVideos", [])
        if not downloaded:
            log("no videos to transcribe")
            return True
        
        # by default prioritize tiktok for srt
        tiktok_vids = [v for v in downloaded if v.get("platform") == "tiktok"]
        to_transcribe = tiktok_vids if tiktok_vids else downloaded[:1]
        
        # check what we already got
        existing_srt = self.job.get("srtFiles", [])
        
        transcriber = WhisperTranscriber(
            model_name=self.settings.get("whisperModel", "base"),
            use_gpu=self.settings.get("useGpu", True),
            output_dir=self.srt_dir
        )
        
        srt_files = list(existing_srt)
        
        for video in to_transcribe:
            video_path = video.get("path")
            if not video_path or not os.path.exists(video_path):
                continue
            
            # check if srt already exists
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            expected_srt = os.path.join(self.srt_dir, f"{base_name}.srt")
            
            if expected_srt in srt_files or os.path.exists(expected_srt):
                log(f"srt already exists: {base_name}")
                if expected_srt not in srt_files:
                    srt_files.append(expected_srt)
                continue
            
            log(f"transcribing: {base_name}")
            
            try:
                srt_path = transcriber.transcribe(video_path)
                if srt_path:
                    srt_files.append(srt_path)
            except Exception as e:
                error(f"transcription failed: {e}")
        
        self.job["srtFiles"] = srt_files
        self.job["progress"] = 40
        self._save_job()
        
        log(f"created {len(srt_files)} SRT files")
        return True
    
    def _step_keywords(self) -> bool:
        """extract keywords from SRT for image search"""
        srt_files = self.job.get("srtFiles", [])
        
        if not srt_files:
            log("no SRT files - using default keywords")
            self.job["keywords"] = ["b-roll", "footage", "stock video"]
            self._save_job()
            return True
        
        extractor = KeywordExtractor()
        all_keywords = []
        
        for srt_path in srt_files:
            if not os.path.exists(srt_path):
                continue
            
            log(f"extracting keywords from: {os.path.basename(srt_path)}")
            keywords = extractor.extract_from_srt(srt_path, max_keywords=40)
            all_keywords.extend(keywords)
        
        # dedupe and limit
        unique_keywords = list(dict.fromkeys(all_keywords))[:50]
        
        self.job["keywords"] = unique_keywords
        self.job["progress"] = 50
        self._save_job()
        
        log(f"extracted {len(unique_keywords)} unique keywords")
        return True
    
    def _step_scrape(self) -> bool:
        """scrape images based on keywords"""
        keywords = self.job.get("keywords", [])
        
        if not keywords:
            error("no keywords to search")
            return False
        
        # check existing images
        existing_images = self.job.get("images", [])
        min_images = self.settings.get("minImages", 15)
        
        if len(existing_images) >= min_images:
            log(f"already have {len(existing_images)} images")
            return True
        
        log(f"scraping images for {len(keywords)} keywords...")
        
        scraper = ImageScraperPro(
            output_dir=self.images_dir,
            min_width=900,  # per spec rule 115
            min_height=700,
            min_size_kb=50
        )
        
        # need this many more images
        needed = min_images - len(existing_images)
        images_per_keyword = max(2, needed // len(keywords) + 1)
        
        all_images = list(existing_images)
        
        for keyword in keywords:
            if len(all_images) >= min_images:
                break
            
            log(f"searching: {keyword}")
            
            try:
                found = scraper.search(keyword, max_images=images_per_keyword)
                all_images.extend(found)
            except Exception as e:
                error(f"search failed for '{keyword}': {e}")
        
        # dedupe images
        unique_images = list(dict.fromkeys(all_images))
        
        self.job["images"] = unique_images
        self.job["progress"] = 70
        self._save_job()
        
        log(f"scraped {len(unique_images)} unique images")
        return len(unique_images) >= min_images // 2  # allow some failure
    
    def _step_render(self) -> bool:
        """create the 3 video outputs"""
        images = self.job.get("images", [])
        downloaded = self.job.get("downloadedVideos", [])
        
        # filter to only existing files
        images = [img for img in images if os.path.exists(img)]
        
        if not images:
            error("no images available for render")
            return False
        
        log(f"rendering with {len(images)} images...")
        
        # get sounds folder
        sounds_folder = self.settings.get("soundsFolder", "")
        if not sounds_folder:
            # use bundled sounds
            sounds_folder = os.path.join(ROOT_DIR, "assets", "sounds")
        
        creator = VideoCreatorPro(
            images_dir=self.images_dir,
            videos_dir=self.downloads_dir,
            output_dir=self.renders_dir,
            sounds_dir=sounds_folder,
            settings=self.settings
        )
        
        outputs = self.job.get("outputs", {})
        
        # output 1: landscape slideshow
        if not outputs.get("slideshow"):
            log("creating landscape slideshow...")
            try:
                slideshow = creator.create_slideshow(
                    images=images,
                    output_name="output_landscape.mp4"
                )
                outputs["slideshow"] = slideshow
                self.job["outputs"] = outputs
                self._save_job()
            except Exception as e:
                error(f"slideshow failed: {e}")
        
        # output 2: portrait split
        if not outputs.get("portrait"):
            log("creating portrait video...")
            try:
                portrait = creator.create_portrait(
                    images=images,
                    output_name="output_portrait.mp4"
                )
                outputs["portrait"] = portrait
                self.job["outputs"] = outputs
                self._save_job()
            except Exception as e:
                error(f"portrait failed: {e}")
        
        # output 3: youtube mix (only youtube sources)
        youtube_vids = [v for v in downloaded if v.get("platform") == "youtube"]
        if youtube_vids and not outputs.get("youtubeMix"):
            log("creating youtube mix...")
            try:
                mix = creator.create_youtube_mix(
                    videos=[v["path"] for v in youtube_vids if os.path.exists(v.get("path", ""))],
                    output_name="output_youtube_mix.mp4"
                )
                outputs["youtubeMix"] = mix
                self.job["outputs"] = outputs
                self._save_job()
            except Exception as e:
                error(f"youtube mix failed: {e}")
        
        self.job["progress"] = 90
        self._save_job()
        
        return True
    
    def _step_validate(self) -> bool:
        """validate all outputs actually work"""
        outputs = self.job.get("outputs", {})
        
        for name, path in outputs.items():
            if not path:
                continue
            
            if not os.path.exists(path):
                error(f"output missing: {name}")
                continue
            
            # check file size
            size = os.path.getsize(path)
            if size < 10000:  # less than 10kb is sus
                error(f"output too small: {name} ({size} bytes)")
                outputs[name] = None
                continue
            
            # try to read with ffprobe
            try:
                import subprocess
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_format", path],
                    capture_output=True,
                    timeout=30
                )
                if result.returncode != 0:
                    error(f"output invalid: {name}")
                    outputs[name] = None
                else:
                    log(f"validated: {name}")
            except Exception:
                # ffprobe not available, just check size
                log(f"validated (size only): {name}")
        
        self.job["outputs"] = outputs
        self.job["progress"] = 100
        self._save_job()
        
        # consider success if at least one output works
        valid_outputs = [v for v in outputs.values() if v]
        return len(valid_outputs) > 0


def main():
    parser = argparse.ArgumentParser(description="Da Editor Job Runner")
    parser.add_argument("--job-folder", required=True, help="Path to job folder")
    parser.add_argument("--settings", required=True, help="JSON string of settings")
    
    args = parser.parse_args()
    
    # parse settings
    try:
        settings = json.loads(args.settings)
    except json.JSONDecodeError:
        error("invalid settings JSON")
        sys.exit(1)
    
    # run the job
    runner = JobRunner(args.job_folder, settings)
    success = runner.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


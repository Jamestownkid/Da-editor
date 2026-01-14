"""
Da Editor - Job Processor
==========================
this is the brain of the operation fr
handles the whole pipeline:

1a. download videos via yt-dlp
1b. transcribe with whisper -> SRT
1c. extract keywords from SRT
1d. scrape images based on keywords
1e. create 3 video outputs
"""

import os
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any


class JobProcessor:
    """
    main processor that runs the whole job pipeline
    
    1a. takes job data and settings
    1b. processes step by step
    1c. reports progress via callbacks
    """
    
    def __init__(
        self,
        job: Dict,
        output_folder: str,
        settings: Dict,
        on_progress: Callable[[str], None] = None,
        on_error: Callable[[str], None] = None
    ):
        self.job = job
        self.job_id = job.get("id", "unknown")
        self.job_folder = os.path.join(output_folder, self.job_id)
        self.settings = settings
        self.on_progress = on_progress or (lambda x: print(f"[Progress] {x}"))
        self.on_error = on_error or (lambda x: print(f"[Error] {x}"))
        
        # 1a. create subdirectories
        self.videos_dir = os.path.join(self.job_folder, "videos")
        self.audio_dir = os.path.join(self.job_folder, "audio")
        self.srt_dir = os.path.join(self.job_folder, "srt")
        self.images_dir = os.path.join(self.job_folder, "images")
        self.output_dir = os.path.join(self.job_folder, "output")
        
        for d in [self.videos_dir, self.audio_dir, self.srt_dir, self.images_dir, self.output_dir]:
            os.makedirs(d, exist_ok=True)
        
        # 1b. track what we got
        self.downloaded_videos = []
        self.srt_files = []
        self.keywords = []
        self.images = []
        
        print(f"[Processor] initialized for job: {self.job_id}")
    
    def run(self):
        """
        main entry point - runs the full pipeline
        processes one step at a time so we can resume
        """
        try:
            self._progress("Starting job...")
            
            # step 1: download videos
            if self.job.get("download_videos", True):
                self._progress("Downloading videos...")
                self._download_videos()
            
            # step 2: generate SRT
            if self.job.get("generate_srt", True):
                self._progress("Transcribing audio...")
                self._generate_srt()
            
            # step 3: extract keywords
            self._progress("Extracting keywords...")
            self._extract_keywords()
            
            # step 4: scrape images
            self._progress("Scraping images...")
            self._scrape_images()
            
            # step 5: create videos
            self._progress("Creating videos...")
            self._create_videos()
            
            self._progress("Job complete!")
            print(f"[Processor] job {self.job_id} completed successfully")
            
        except Exception as e:
            self._error(f"Job failed: {e}")
            raise
    
    def _progress(self, msg: str):
        """report progress"""
        if self.on_progress:
            self.on_progress(msg)
    
    def _error(self, msg: str):
        """report error"""
        if self.on_error:
            self.on_error(msg)
    
    def _download_videos(self):
        """
        1a. download all videos from links using yt-dlp
        handles youtube, tiktok, instagram, etc
        """
        from core.downloader import VideoDownloader
        
        downloader = VideoDownloader(
            output_dir=self.videos_dir,
            on_progress=self._progress
        )
        
        links = self.job.get("links", [])
        for i, link in enumerate(links):
            self._progress(f"Downloading {i+1}/{len(links)}: {link[:50]}...")
            try:
                video_path = downloader.download(link)
                if video_path:
                    self.downloaded_videos.append({
                        "url": link,
                        "path": video_path,
                        "platform": self._detect_platform(link)
                    })
            except Exception as e:
                self._error(f"Failed to download {link}: {e}")
        
        # save download info
        self._save_state()
        print(f"[Processor] downloaded {len(self.downloaded_videos)} videos")
    
    def _detect_platform(self, url: str) -> str:
        """detect which platform a url is from"""
        url_lower = url.lower()
        if "tiktok.com" in url_lower:
            return "tiktok"
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        elif "instagram.com" in url_lower:
            return "instagram"
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            return "twitter"
        else:
            return "other"
    
    def _generate_srt(self):
        """
        1b. transcribe videos to SRT using whisper
        default: use tiktok videos for SRT
        """
        from core.transcriber import WhisperTranscriber
        
        # by default, prioritize tiktok for SRT
        tiktok_videos = [v for v in self.downloaded_videos if v["platform"] == "tiktok"]
        videos_to_transcribe = tiktok_videos if tiktok_videos else self.downloaded_videos[:1]
        
        if not videos_to_transcribe:
            self._progress("No videos to transcribe")
            return
        
        transcriber = WhisperTranscriber(
            model_name=self.settings.get("whisper_model", "base"),
            use_gpu=self.settings.get("use_gpu", True),
            output_dir=self.srt_dir
        )
        
        for video in videos_to_transcribe:
            self._progress(f"Transcribing: {os.path.basename(video['path'])}")
            try:
                srt_path = transcriber.transcribe(video["path"])
                if srt_path:
                    self.srt_files.append(srt_path)
            except Exception as e:
                self._error(f"Transcription failed: {e}")
        
        self._save_state()
        print(f"[Processor] created {len(self.srt_files)} SRT files")
    
    def _extract_keywords(self):
        """
        1c. extract keywords from SRT for image search
        using basic NLP - nouns and key phrases
        """
        from core.keyword_extractor import KeywordExtractor
        
        extractor = KeywordExtractor()
        
        for srt_path in self.srt_files:
            try:
                keywords = extractor.extract_from_srt(srt_path)
                self.keywords.extend(keywords)
            except Exception as e:
                self._error(f"Keyword extraction failed: {e}")
        
        # dedupe and limit
        self.keywords = list(set(self.keywords))[:50]
        
        self._save_state()
        print(f"[Processor] extracted {len(self.keywords)} keywords")
    
    def _scrape_images(self):
        """
        1d. scrape google images based on keywords
        using playwright for reliable scraping
        """
        from core.image_scraper import ImageScraper
        
        if not self.keywords:
            self._progress("No keywords - using default images")
            return
        
        scraper = ImageScraper(
            output_dir=self.images_dir,
            min_width=1000,
            min_height=800
        )
        
        min_images = self.settings.get("min_images", 11)
        images_per_keyword = max(2, min_images // len(self.keywords) + 1)
        
        for keyword in self.keywords:
            self._progress(f"Searching: {keyword}")
            try:
                found_images = scraper.search(keyword, max_images=images_per_keyword)
                self.images.extend(found_images)
            except Exception as e:
                self._error(f"Image search failed for '{keyword}': {e}")
            
            # check if we have enough
            if len(self.images) >= min_images:
                break
        
        # dedupe by path
        seen = set()
        unique_images = []
        for img in self.images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)
        self.images = unique_images
        
        self._save_state()
        print(f"[Processor] scraped {len(self.images)} images")
    
    def _create_videos(self):
        """
        1e. create the 3 video outputs:
        - landscape slideshow with images
        - portrait split (for tiktok/ig)  
        - youtube video mix
        """
        from core.video_creator import VideoCreator
        
        creator = VideoCreator(
            images_dir=self.images_dir,
            videos_dir=self.videos_dir,
            output_dir=self.output_dir,
            sounds_dir=self.settings.get("sounds_folder", ""),
            settings=self.settings
        )
        
        # get audio from SRT source video if available
        audio_source = None
        if self.srt_files:
            # find the video that matches the first srt
            srt_name = os.path.splitext(os.path.basename(self.srt_files[0]))[0]
            for video in self.downloaded_videos:
                if srt_name in os.path.basename(video["path"]):
                    audio_source = video["path"]
                    break
        
        # video 1: landscape slideshow
        self._progress("Creating landscape slideshow...")
        try:
            slideshow_path = creator.create_slideshow(
                images=self.images,
                audio_source=audio_source,
                srt_path=self.srt_files[0] if self.srt_files else None,
                output_name="output_slideshow.mp4"
            )
            self.job["outputs"]["slideshow"] = slideshow_path
        except Exception as e:
            self._error(f"Slideshow creation failed: {e}")
        
        # video 2: portrait split
        self._progress("Creating portrait video...")
        try:
            portrait_path = creator.create_portrait(
                images=self.images,
                output_name="output_portrait.mp4"
            )
            self.job["outputs"]["portrait"] = portrait_path
        except Exception as e:
            self._error(f"Portrait creation failed: {e}")
        
        # video 3: youtube video mix
        youtube_videos = [v for v in self.downloaded_videos if v["platform"] == "youtube"]
        if youtube_videos:
            self._progress("Creating YouTube mix...")
            try:
                mix_path = creator.create_youtube_mix(
                    videos=[v["path"] for v in youtube_videos],
                    output_name="output_youtube_mix.mp4"
                )
                self.job["outputs"]["youtube_mix"] = mix_path
            except Exception as e:
                self._error(f"YouTube mix failed: {e}")
        
        self._save_state()
        print(f"[Processor] videos created in {self.output_dir}")
    
    def _save_state(self):
        """save current job state to json"""
        state = {
            **self.job,
            "downloaded_videos": self.downloaded_videos,
            "srt_files": self.srt_files,
            "keywords": self.keywords,
            "images": self.images,
            "last_updated": datetime.now().isoformat()
        }
        
        json_path = os.path.join(self.job_folder, "job.json")
        with open(json_path, "w") as f:
            json.dump(state, f, indent=2)

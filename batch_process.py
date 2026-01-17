#!/usr/bin/env python3
"""
Batch processor for brollsuff folder jobs
Processes each folder: download -> SRT (TikTok) -> B-roll (YouTube)
"""
import os
import sys
import json
import time
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.downloader import VideoDownloader
from core.transcriber import WhisperTranscriber
from core.keyword_extractor import KeywordExtractor
from core.image_scraper_pro import ImageScraperPro
from core.video_creator_pro import VideoCreatorPro

BROLLSUFF = "/home/admin/Downloads/brollsuff"
SKIP_FOLDERS = ["ncie"]  # Skip this folder per user request
MAX_JOB_TIME = 25 * 60  # 25 minutes max per job

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def parse_links_txt(links_path):
    """Parse links.txt and return TikTok URLs (for SRT) and YouTube URLs (for B-roll)"""
    tiktok_urls = []
    youtube_urls = []
    
    if not os.path.exists(links_path):
        return tiktok_urls, youtube_urls
    
    with open(links_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Extract URL (before any markers like [SRT][IMG])
            url = line.split()[0] if line.split() else line
            
            if 'tiktok.com' in url.lower():
                needs_srt = '[SRT]' in line or '[srt]' in line
                tiktok_urls.append({'url': url, 'srt': needs_srt})
            elif 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
                youtube_urls.append({'url': url})
    
    return tiktok_urls, youtube_urls

def process_folder(folder_path, folder_name):
    """Process a single job folder"""
    job_start = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    log(f"\n{'='*60}")
    log(f"PROCESSING: {folder_name}")
    log(f"{'='*60}")
    
    links_path = os.path.join(folder_path, "links.txt")
    images_dir = os.path.join(folder_path, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # Parse links
    tiktok_urls, youtube_urls = parse_links_txt(links_path)
    log(f"Found: {len(tiktok_urls)} TikTok, {len(youtube_urls)} YouTube")
    
    if not tiktok_urls and not youtube_urls:
        log("  No valid links found, skipping...")
        return False
    
    downloader = VideoDownloader(output_dir=folder_path)
    downloaded_tiktok = []
    downloaded_youtube = []
    
    # Step 1: Download TikTok videos (for SRT)
    log("\n[STEP 1] Downloading TikTok videos...")
    for i, url_data in enumerate(tiktok_urls):
        if time.time() - job_start > MAX_JOB_TIME:
            log("  Time limit reached, using what we have...")
            break
        
        url = url_data['url']
        # Check if already downloaded
        existing = [f for f in os.listdir(folder_path) if f.endswith('.mp4') and 'tiktok' in f.lower() or 'crime' in f.lower() or 'zeph' in f.lower()]
        
        if existing:
            log(f"  TikTok already downloaded: {existing[0][:40]}...")
            downloaded_tiktok.append(os.path.join(folder_path, existing[0]))
        else:
            log(f"  Downloading TikTok [{i+1}/{len(tiktok_urls)}]...")
            try:
                path = downloader.download(url)
                if path:
                    downloaded_tiktok.append(path)
                    log(f"    ✓ {os.path.basename(path)[:40]}...")
            except Exception as e:
                log(f"    ✗ Failed: {str(e)[:50]}")
    
    # Step 2: Download YouTube videos (for B-roll)
    log("\n[STEP 2] Downloading YouTube videos...")
    for i, url_data in enumerate(youtube_urls):
        if time.time() - job_start > MAX_JOB_TIME:
            log("  Time limit reached, using what we have...")
            break
        
        url = url_data['url']
        # Check if already downloaded
        existing_yt = [f for f in os.listdir(folder_path) if f.endswith('.mp4') and not any(x in f.lower() for x in ['broll', 'output', 'tiktok'])]
        
        if existing_yt:
            log(f"  YouTube already downloaded: {existing_yt[0][:40]}...")
            downloaded_youtube.append(os.path.join(folder_path, existing_yt[0]))
        else:
            log(f"  Downloading YouTube [{i+1}/{len(youtube_urls)}]...")
            try:
                path = downloader.download(url)
                if path:
                    downloaded_youtube.append(path)
                    log(f"    ✓ {os.path.basename(path)[:40]}...")
            except Exception as e:
                log(f"    ✗ Failed: {str(e)[:50]}")
    
    # Step 3: Generate SRT from TikTok videos
    srt_files = []
    if downloaded_tiktok:
        log("\n[STEP 3] Generating SRT from TikTok...")
        
        # Check for existing SRT
        existing_srt = [f for f in os.listdir(folder_path) if f.endswith('.srt')]
        if existing_srt:
            log(f"  SRT already exists: {existing_srt[0]}")
            srt_files = [os.path.join(folder_path, f) for f in existing_srt]
        else:
            try:
                transcriber = WhisperTranscriber(model_name="small", use_gpu=True, output_dir=folder_path)
                for video in downloaded_tiktok[:1]:  # Just first TikTok for SRT
                    if time.time() - job_start > MAX_JOB_TIME:
                        break
                    srt_path = transcriber.transcribe(video)
                    if srt_path:
                        srt_files.append(srt_path)
                        log(f"    ✓ {os.path.basename(srt_path)}")
            except Exception as e:
                log(f"    ✗ SRT failed: {str(e)[:50]}")
    
    # Step 4: Extract keywords
    keywords = []
    if srt_files:
        log("\n[STEP 4] Extracting keywords...")
        try:
            extractor = KeywordExtractor()
            for srt in srt_files:
                kw = extractor.extract_from_srt(srt)
                keywords.extend(kw)
            keywords = list(dict.fromkeys(keywords))[:15]
            log(f"    Found {len(keywords)} keywords: {keywords[:5]}...")
        except Exception as e:
            log(f"    ✗ Keywords failed: {str(e)[:50]}")
            keywords = ["nature", "food", "cooking", "life", "science"]
    
    if not keywords:
        keywords = ["nature", "food", "cooking", "life", "science"]
    
    # Step 5: Scrape images
    images = []
    existing_images = [os.path.join(images_dir, f) for f in os.listdir(images_dir) if f.endswith(('.jpg', '.png', '.webp'))]
    
    if len(existing_images) >= 10:
        log(f"\n[STEP 5] Using {len(existing_images)} existing images...")
        images = existing_images
    else:
        log("\n[STEP 5] Scraping images...")
        try:
            scraper = ImageScraperPro(output_dir=images_dir, min_width=800, min_height=600)
            for kw in keywords[:5]:
                if time.time() - job_start > MAX_JOB_TIME:
                    break
                if len(images) >= 20:
                    break
                log(f"    Searching: {kw}...")
                found = scraper.search(kw, max_images=5)
                images.extend(found)
            log(f"    Total: {len(images)} images")
        except Exception as e:
            log(f"    ✗ Scraping failed: {str(e)[:50]}")
    
    if not images:
        images = existing_images or []
    
    if len(images) < 5:
        log("  Not enough images, trying to use from other folders...")
        for other_folder in os.listdir(BROLLSUFF):
            other_path = os.path.join(BROLLSUFF, other_folder, "images")
            if os.path.isdir(other_path) and other_folder != folder_name:
                for f in os.listdir(other_path)[:5]:
                    if f.endswith(('.jpg', '.png', '.webp')):
                        images.append(os.path.join(other_path, f))
                if len(images) >= 10:
                    break
    
    # Step 6: Create video outputs
    if images and len(images) >= 5:
        log(f"\n[STEP 6] Creating video outputs with {len(images)} images...")
        
        try:
            creator = VideoCreatorPro(
                images_dir=images_dir,
                videos_dir=folder_path,
                output_dir=folder_path,
                settings={
                    'secondsPerImage': 2.5,
                    'bgColor': '#FFFFFF',
                    'soundVolume': 1.0,
                    'motionLevel': 'off',  # No motion to prevent shakiness
                    'targetDuration': 60
                }
            )
            
            # Output 1: Landscape slideshow
            if time.time() - job_start < MAX_JOB_TIME:
                log("    Creating output_video.mp4...")
                out1 = creator.create_slideshow(images[:20], f"output_video_{timestamp}.mp4")
                if out1:
                    log(f"      ✓ {os.path.getsize(out1)/1024/1024:.1f} MB")
            
            # Output 2: Portrait (Instagram)
            if time.time() - job_start < MAX_JOB_TIME:
                log("    Creating broll_instagram.mp4...")
                out2 = creator.create_portrait(images[:15], f"broll_instagram_{timestamp}.mp4")
                if out2:
                    log(f"      ✓ {os.path.getsize(out2)/1024/1024:.1f} MB")
            
            # Output 3: YouTube mix (ONLY YouTube videos)
            if downloaded_youtube and time.time() - job_start < MAX_JOB_TIME:
                log("    Creating broll_youtube.mp4...")
                out3 = creator.create_youtube_mix(downloaded_youtube, f"broll_youtube_{timestamp}.mp4")
                if out3:
                    log(f"      ✓ {os.path.getsize(out3)/1024/1024:.1f} MB")
            
        except Exception as e:
            log(f"    ✗ Video creation failed: {str(e)[:100]}")
    else:
        log("  Not enough images for video creation")
    
    elapsed = time.time() - job_start
    log(f"\n[DONE] {folder_name} completed in {elapsed/60:.1f} minutes")
    
    return True

def main():
    log("="*60)
    log("BATCH PROCESSOR - Processing all brollsuff folders")
    log("="*60)
    
    folders = [f for f in os.listdir(BROLLSUFF) 
               if os.path.isdir(os.path.join(BROLLSUFF, f)) 
               and f not in SKIP_FOLDERS
               and not f.endswith('.json')]
    
    log(f"Found {len(folders)} folders to process (skipping: {SKIP_FOLDERS})")
    
    results = {}
    for i, folder in enumerate(sorted(folders)):
        folder_path = os.path.join(BROLLSUFF, folder)
        log(f"\n[{i+1}/{len(folders)}] Starting {folder}...")
        
        try:
            success = process_folder(folder_path, folder)
            results[folder] = "✓" if success else "⚠"
        except Exception as e:
            log(f"ERROR in {folder}: {e}")
            results[folder] = "✗"
    
    log("\n" + "="*60)
    log("BATCH COMPLETE - Results:")
    log("="*60)
    for folder, status in results.items():
        log(f"  {status} {folder}")

if __name__ == "__main__":
    main()


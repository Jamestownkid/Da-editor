#!/usr/bin/env python3
"""
Full test script to verify the entire pipeline works.
Tests: download -> transcribe -> scrape images -> create 3 video outputs
"""
import os
import sys
import json
import time
import shutil

# Add core to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.downloader import VideoDownloader
from core.transcriber import WhisperTranscriber as Transcriber
from core.keyword_extractor import KeywordExtractor
from core.image_scraper_pro import ImageScraperPro
from core.video_creator_pro import VideoCreatorPro

# Test config
TEST_DIR = "/home/admin/Downloads/tessss"
JOB_NAME = "full_test_job"
JOB_DIR = os.path.join(TEST_DIR, JOB_NAME)

# Test links
LINKS = [
    "https://www.tiktok.com/@gravityassistus/video/7584165521193520415",
    "https://www.youtube.com/watch?v=1qAc22WxsWA"
]

def setup_job():
    """Create job folder structure"""
    os.makedirs(JOB_DIR, exist_ok=True)
    os.makedirs(os.path.join(JOB_DIR, "videos"), exist_ok=True)
    os.makedirs(os.path.join(JOB_DIR, "images"), exist_ok=True)
    os.makedirs(os.path.join(JOB_DIR, "srt"), exist_ok=True)
    
    # Save links
    with open(os.path.join(JOB_DIR, "links.txt"), "w") as f:
        f.write("\n".join(LINKS))
    
    # Create job.json
    job = {
        "id": JOB_NAME,
        "name": JOB_NAME,
        "status": "pending",
        "links": LINKS,
        "createdAt": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(os.path.join(JOB_DIR, "job.json"), "w") as f:
        json.dump(job, f, indent=2)
    
    print(f"[Test] Job folder created: {JOB_DIR}")
    return job

def test_download():
    """Test video downloads"""
    print("\n" + "="*50)
    print("[Test] STEP 1: Downloading videos...")
    print("="*50)
    
    downloader = VideoDownloader(os.path.join(JOB_DIR, "videos"))
    downloaded = []
    
    for link in LINKS:
        print(f"\n[Test] Downloading: {link[:50]}...")
        try:
            path = downloader.download(link)
            if path and os.path.exists(path):
                size = os.path.getsize(path) / 1024 / 1024
                print(f"[Test] SUCCESS: {os.path.basename(path)} ({size:.1f} MB)")
                downloaded.append(path)
            else:
                print(f"[Test] FAILED: No file returned")
        except Exception as e:
            print(f"[Test] ERROR: {e}")
    
    print(f"\n[Test] Downloaded {len(downloaded)}/{len(LINKS)} videos")
    return downloaded

def test_transcribe(videos):
    """Test transcription"""
    print("\n" + "="*50)
    print("[Test] STEP 2: Transcribing videos...")
    print("="*50)
    
    transcriber = Transcriber(
        model_name="small",
        output_dir=os.path.join(JOB_DIR, "srt")
    )
    
    srt_files = []
    for video in videos:
        print(f"\n[Test] Transcribing: {os.path.basename(video)}...")
        try:
            srt_path = transcriber.transcribe(video)
            if srt_path and os.path.exists(srt_path):
                print(f"[Test] SUCCESS: {os.path.basename(srt_path)}")
                srt_files.append(srt_path)
            else:
                print(f"[Test] FAILED: No SRT generated")
        except Exception as e:
            print(f"[Test] ERROR: {e}")
    
    print(f"\n[Test] Transcribed {len(srt_files)}/{len(videos)} videos")
    return srt_files

def test_keywords(srt_files):
    """Test keyword extraction"""
    print("\n" + "="*50)
    print("[Test] STEP 3: Extracting keywords...")
    print("="*50)
    
    extractor = KeywordExtractor()
    all_keywords = []
    
    for srt in srt_files:
        print(f"\n[Test] Extracting from: {os.path.basename(srt)}...")
        try:
            keywords = extractor.extract_from_srt(srt)
            print(f"[Test] Found {len(keywords)} keywords: {keywords[:5]}...")
            all_keywords.extend(keywords)
        except Exception as e:
            print(f"[Test] ERROR: {e}")
    
    # Dedupe and limit
    unique = list(dict.fromkeys(all_keywords))[:10]
    print(f"\n[Test] Total unique keywords: {len(unique)}")
    return unique

def test_scrape(keywords):
    """Test image scraping"""
    print("\n" + "="*50)
    print("[Test] STEP 4: Scraping images...")
    print("="*50)
    
    scraper = ImageScraperPro(
        output_dir=os.path.join(JOB_DIR, "images"),
        min_width=800,
        min_height=600
    )
    
    all_images = []
    for kw in keywords[:5]:  # Limit to 5 keywords for speed
        print(f"\n[Test] Searching: '{kw}'...")
        try:
            images = scraper.search(kw, max_images=5)
            print(f"[Test] Got {len(images)} images")
            all_images.extend(images)
        except Exception as e:
            print(f"[Test] ERROR: {e}")
    
    # Browser cleanup is handled internally by scraper
    print(f"\n[Test] Total images scraped: {len(all_images)}")
    return all_images

def test_video_creation(images, videos):
    """Test video creation - all 3 outputs"""
    print("\n" + "="*50)
    print("[Test] STEP 5: Creating video outputs...")
    print("="*50)
    
    # Find sounds folder
    sounds_dir = ""
    possible_sounds = [
        "/home/admin/Downloads/Da-editor/assets/sounds",
        "/home/admin/Downloads/brollsuff/sounds",
        os.path.expanduser("~/Downloads/sounds")
    ]
    for sd in possible_sounds:
        if os.path.isdir(sd):
            sounds_dir = sd
            break
    
    creator = VideoCreatorPro(
        images_dir=os.path.join(JOB_DIR, "images"),
        videos_dir=os.path.join(JOB_DIR, "videos"),
        output_dir=JOB_DIR,
        sounds_dir=sounds_dir,
        settings={
            "secondsPerImage": 4.0,
            "bgColor": "#FFFFFF",
            "soundVolume": 1.0,
            "targetDuration": 60
        }
    )
    
    outputs = []
    
    # Output 1: Landscape slideshow
    print("\n[Test] Creating OUTPUT 1: Landscape slideshow...")
    try:
        out1 = creator.create_slideshow(images, "output_video.mp4")
        if out1 and os.path.exists(out1):
            size = os.path.getsize(out1) / 1024 / 1024
            print(f"[Test] SUCCESS: output_video.mp4 ({size:.1f} MB)")
            outputs.append(out1)
        else:
            print("[Test] FAILED: output_video.mp4 not created")
    except Exception as e:
        print(f"[Test] ERROR: {e}")
    
    # Output 2: Portrait (Instagram/TikTok)
    print("\n[Test] Creating OUTPUT 2: Portrait video...")
    try:
        out2 = creator.create_portrait(images, "broll_instagram.mp4")
        if out2 and os.path.exists(out2):
            size = os.path.getsize(out2) / 1024 / 1024
            print(f"[Test] SUCCESS: broll_instagram.mp4 ({size:.1f} MB)")
            outputs.append(out2)
        else:
            print("[Test] FAILED: broll_instagram.mp4 not created")
    except Exception as e:
        print(f"[Test] ERROR: {e}")
    
    # Output 3: YouTube mix
    print("\n[Test] Creating OUTPUT 3: YouTube mix...")
    try:
        out3 = creator.create_youtube_mix(videos, "broll_youtube.mp4")
        if out3 and os.path.exists(out3):
            size = os.path.getsize(out3) / 1024 / 1024
            print(f"[Test] SUCCESS: broll_youtube.mp4 ({size:.1f} MB)")
            outputs.append(out3)
        else:
            print("[Test] FAILED: broll_youtube.mp4 not created")
    except Exception as e:
        print(f"[Test] ERROR: {e}")
    
    return outputs

def main():
    print("="*60)
    print("  DA EDITOR - FULL PIPELINE TEST")
    print("="*60)
    
    # Setup
    job = setup_job()
    
    # Step 1: Download
    videos = test_download()
    if not videos:
        print("\n[Test] ABORT: No videos downloaded")
        return False
    
    # Step 2: Transcribe
    srt_files = test_transcribe(videos)
    
    # Step 3: Keywords (fallback to defaults if transcription failed)
    if srt_files:
        keywords = test_keywords(srt_files)
    else:
        print("\n[Test] Using fallback keywords...")
        keywords = ["space", "earth", "planet", "universe", "science", "nature"]
    
    # Step 4: Scrape images
    images = test_scrape(keywords)
    if not images:
        print("\n[Test] ABORT: No images scraped")
        return False
    
    # Step 5: Create videos
    outputs = test_video_creation(images, videos)
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    print(f"  Videos downloaded: {len(videos)}")
    print(f"  SRT files created: {len(srt_files)}")
    print(f"  Keywords extracted: {len(keywords)}")
    print(f"  Images scraped: {len(images)}")
    print(f"  Video outputs created: {len(outputs)}/3")
    print("="*60)
    
    # List final folder
    print(f"\n[Test] Final contents of {JOB_DIR}:")
    for item in sorted(os.listdir(JOB_DIR)):
        path = os.path.join(JOB_DIR, item)
        if os.path.isfile(path):
            size = os.path.getsize(path) / 1024 / 1024
            print(f"  - {item} ({size:.2f} MB)")
        else:
            count = len(os.listdir(path))
            print(f"  - {item}/ ({count} items)")
    
    return len(outputs) >= 2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


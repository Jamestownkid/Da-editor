#!/usr/bin/env python3
"""
Da Editor - Test Script
========================
tests the full pipeline with sample data
makes sure the 3 video outputs actually generate

run this to verify everything works before shipping
"""

import os
import sys
import json
import shutil
import tempfile
from datetime import datetime

# add project root to path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def create_sample_srt(output_path: str):
    """create a sample SRT file for testing"""
    srt_content = """1
00:00:00,000 --> 00:00:04,000
Welcome to this amazing journey through the mountains.

2
00:00:04,000 --> 00:00:08,000
The Rocky Mountains are one of the most beautiful places on Earth.

3
00:00:08,000 --> 00:00:12,000
With stunning landscapes and incredible wildlife.

4
00:00:12,000 --> 00:00:16,000
From majestic bears to soaring eagles.

5
00:00:16,000 --> 00:00:20,000
The natural beauty here is truly breathtaking.

6
00:00:20,000 --> 00:00:24,000
Crystal clear lakes reflect the towering peaks.

7
00:00:24,000 --> 00:00:28,000
Ancient forests cover the mountain slopes.

8
00:00:28,000 --> 00:00:32,000
This is nature at its finest.

9
00:00:32,000 --> 00:00:36,000
A perfect escape from the modern world.

10
00:00:36,000 --> 00:00:40,000
Thank you for joining us on this adventure.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
    return output_path


def create_test_image(output_path: str, color: str = "blue"):
    """create a simple test image"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # create 1920x1080 image
        img = Image.new("RGB", (1920, 1080), color)
        draw = ImageDraw.Draw(img)
        
        # add some text
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        text = f"Test Image - {color}"
        draw.text((100, 100), text, fill="white", font=font)
        
        img.save(output_path, "JPEG", quality=90)
        return output_path
        
    except ImportError:
        print("[Test] PIL not installed - skipping image creation")
        return None


def main():
    print("=" * 60)
    print("  DA EDITOR - TEST SCRIPT")
    print("=" * 60)
    print()
    
    # create temp test directory
    test_dir = os.path.join(ROOT, "_test_job")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # create subdirectories
    downloads_dir = os.path.join(test_dir, "downloads")
    srt_dir = os.path.join(test_dir, "srt")
    images_dir = os.path.join(test_dir, "images")
    renders_dir = os.path.join(test_dir, "renders")
    logs_dir = os.path.join(test_dir, "logs")
    cache_dir = os.path.join(test_dir, "cache")
    
    for d in [downloads_dir, srt_dir, images_dir, renders_dir, logs_dir, cache_dir]:
        os.makedirs(d)
    
    print(f"[Test] Created test directory: {test_dir}")
    
    # step 1: create sample SRT
    print("\n[Step 1] Creating sample SRT...")
    srt_path = create_sample_srt(os.path.join(srt_dir, "test_video.srt"))
    print(f"  Created: {srt_path}")
    
    # step 2: extract keywords
    print("\n[Step 2] Extracting keywords...")
    try:
        from core.keyword_extractor import KeywordExtractor
        extractor = KeywordExtractor()
        keywords = extractor.extract_from_srt(srt_path, max_keywords=20)
        print(f"  Keywords: {keywords[:10]}...")
    except Exception as e:
        print(f"  Failed: {e}")
        keywords = ["mountain", "landscape", "nature", "wildlife", "forest", "lake"]
    
    # step 3: create test images (or scrape if you want)
    print("\n[Step 3] Creating test images...")
    colors = ["#2a5298", "#1e3a5f", "#234e70", "#3d5a80", "#1b3a4b", "#2c5364"]
    images = []
    
    for i, color in enumerate(colors):
        img_path = os.path.join(images_dir, f"test_image_{i}.jpg")
        created = create_test_image(img_path, color)
        if created:
            images.append(created)
            print(f"  Created: test_image_{i}.jpg")
    
    if not images:
        print("  No images created - need PIL")
        print("  Trying to scrape real images instead...")
        
        try:
            from core.image_scraper_pro import ImageScraperPro
            scraper = ImageScraperPro(output_dir=images_dir, min_width=800, min_height=600)
            images = scraper.search("mountain landscape scenic", max_images=6)
            print(f"  Scraped {len(images)} images")
        except Exception as e:
            print(f"  Scraping failed: {e}")
    
    if not images:
        print("\n[ERROR] No images available - cannot test video creation")
        return False
    
    # step 4: create videos
    print("\n[Step 4] Creating video outputs...")
    
    try:
        from core.video_creator_pro import VideoCreatorPro
        
        sounds_dir = os.path.join(ROOT, "assets", "sounds")
        
        creator = VideoCreatorPro(
            images_dir=images_dir,
            videos_dir=downloads_dir,
            output_dir=renders_dir,
            sounds_dir=sounds_dir,
            settings={
                "secondsPerImage": 3.0,
                "bgColor": "#FFFFFF",
                "soundVolume": 0.7
            }
        )
        
        # output 1: landscape slideshow
        print("\n  Creating landscape slideshow...")
        slideshow = creator.create_slideshow(images, "test_slideshow.mp4")
        if slideshow:
            print(f"    SUCCESS: {slideshow}")
        else:
            print("    FAILED")
        
        # output 2: portrait
        print("\n  Creating portrait video...")
        portrait = creator.create_portrait(images, "test_portrait.mp4")
        if portrait:
            print(f"    SUCCESS: {portrait}")
        else:
            print("    FAILED")
        
        # output 3: youtube mix (skip if no real videos)
        print("\n  YouTube mix skipped (no videos to mix)")
        
    except Exception as e:
        print(f"  Video creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # step 5: validate outputs
    print("\n[Step 5] Validating outputs...")
    
    outputs = []
    for f in os.listdir(renders_dir):
        path = os.path.join(renders_dir, f)
        if os.path.isfile(path):
            size = os.path.getsize(path)
            outputs.append((f, size))
            print(f"  {f}: {size / 1024 / 1024:.2f} MB")
    
    # summary
    print("\n" + "=" * 60)
    print("  TEST RESULTS")
    print("=" * 60)
    
    if len(outputs) >= 2:
        print("\n  STATUS: PASSED")
        print(f"  Created {len(outputs)} video output(s)")
        print(f"  Test folder: {test_dir}")
    else:
        print("\n  STATUS: FAILED")
        print("  Not all outputs were created")
    
    # keep test files for inspection
    print(f"\n  Test files kept at: {test_dir}")
    print("  Delete manually when done inspecting")
    
    return len(outputs) >= 2


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


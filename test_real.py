#!/usr/bin/env python3
"""
Da Editor - Real Test with User Links
======================================
tests the full pipeline with the actual tiktok and youtube links
"""

import os
import sys
import json
import shutil
import tempfile
from datetime import datetime

# add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.job_runner import JobRunner


def test_real_pipeline():
    """
    test with the actual links user provided:
    - TikTok: https://www.tiktok.com/@zephzoid/video/7570107046410849591 [SRT][IMG]
    - YouTube: https://www.youtube.com/watch?v=Wtp2Fgbd1fQ
    """
    print("=" * 60)
    print("Da Editor - Real Pipeline Test")
    print("=" * 60)
    
    # create test folder
    test_folder = os.path.join(tempfile.gettempdir(), f"da_editor_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(test_folder, exist_ok=True)
    
    print(f"\nTest folder: {test_folder}")
    
    # create job.json with the actual links
    job_data = {
        "name": "test_job",
        "status": "pending",
        "created": datetime.now().isoformat(),
        "urls": [
            {
                "url": "https://www.tiktok.com/@zephzoid/video/7570107046410849591",
                "srt": True,
                "images": True
            },
            {
                "url": "https://www.youtube.com/watch?v=Wtp2Fgbd1fQ",
                "srt": False,
                "images": False
            }
        ]
    }
    
    # save job.json
    job_json_path = os.path.join(test_folder, "job.json")
    with open(job_json_path, "w") as f:
        json.dump(job_data, f, indent=2)
    
    print("\nJob created:")
    print(f"  - TikTok link (SRT + Images enabled)")
    print(f"  - YouTube link (will be used for output #3)")
    
    # settings
    settings = {
        "whisperModel": "medium",  # user requested medium
        "useGpu": True,
        "outputFolder": test_folder,
        "soundsFolder": os.path.join(os.path.dirname(__file__), "assets", "sounds"),
        "secondsPerImage": 4.0,
        "soundVolume": 1.0,
        "minImages": 8,
        "bgColor": "#FFFFFF"
    }
    
    print("\nSettings:")
    print(f"  - Whisper model: {settings['whisperModel']}")
    print(f"  - GPU: {settings['useGpu']}")
    print(f"  - Min images: {settings['minImages']}")
    
    # run the job
    print("\n" + "-" * 60)
    print("Starting pipeline...")
    print("-" * 60 + "\n")
    
    runner = JobRunner(test_folder, settings)
    success = runner.run()
    
    print("\n" + "-" * 60)
    print("Pipeline complete!")
    print("-" * 60)
    
    # check results
    print("\nResults:")
    
    # check downloads
    downloads = [f for f in os.listdir(test_folder) if f.endswith(".mp4") and not f.startswith("broll_") and not f.startswith("output_")]
    print(f"\n  Downloaded videos: {len(downloads)}")
    for d in downloads:
        size = os.path.getsize(os.path.join(test_folder, d)) / (1024*1024)
        print(f"    - {d} ({size:.1f}MB)")
    
    # check SRT
    srt_files = [f for f in os.listdir(test_folder) if f.endswith(".srt")]
    print(f"\n  SRT files: {len(srt_files)}")
    for s in srt_files:
        print(f"    - {s}")
    
    # check images
    images_dir = os.path.join(test_folder, "images")
    if os.path.exists(images_dir):
        images = os.listdir(images_dir)
        print(f"\n  Images scraped: {len(images)}")
    
    # check outputs (the 3 videos)
    outputs = {
        "output_video.mp4": "Landscape B-roll (Output #1)",
        "broll_instagram": "Portrait/Instagram (Output #2)",
        "broll_youtube": "YouTube Mix (Output #3)"
    }
    
    print(f"\n  Video outputs:")
    for pattern, desc in outputs.items():
        found = [f for f in os.listdir(test_folder) if f.startswith(pattern.replace(".mp4", "")) and f.endswith(".mp4")]
        if found:
            for f in found:
                size = os.path.getsize(os.path.join(test_folder, f)) / (1024*1024)
                print(f"    + {desc}: {f} ({size:.1f}MB)")
        else:
            print(f"    - {desc}: NOT FOUND")
    
    # reload job to see final state
    with open(job_json_path, "r") as f:
        final_job = json.load(f)
    
    print(f"\n  Final job status: {final_job.get('status')}")
    
    if final_job.get("valid_outputs"):
        print(f"  Valid outputs: {list(final_job['valid_outputs'].keys())}")
    
    print(f"\n  Test folder: {test_folder}")
    print("  (folder not deleted so you can inspect the results)")
    
    return success


if __name__ == "__main__":
    try:
        success = test_real_pipeline()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


"""
Da Editor - Utilities
======================
helper functions used across the app
nothing too crazy just the basics
"""

import os
import re
import hashlib
from datetime import datetime


def safe_filename(text: str, max_length: int = 50) -> str:
    """
    1a. make a string safe for use as filename
    removes special chars, limits length
    """
    # remove special characters
    safe = re.sub(r'[^\w\s-]', '', text)
    # replace spaces with underscores
    safe = re.sub(r'\s+', '_', safe)
    # limit length
    if len(safe) > max_length:
        safe = safe[:max_length]
    return safe.strip('_')


def ensure_dir(path: str) -> str:
    """
    1b. make sure directory exists, create if not
    returns the path
    """
    os.makedirs(path, exist_ok=True)
    return path


def get_file_hash(filepath: str) -> str:
    """
    1c. get md5 hash of file contents
    useful for deduping
    """
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def format_duration(seconds: float) -> str:
    """
    2a. format seconds to human readable duration
    like "1:23:45" or "5:30"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_bytes(size: int) -> str:
    """
    2b. format bytes to human readable size
    like "1.5 GB" or "256 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def timestamp_now() -> str:
    """
    2c. get current timestamp as string
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_video_file(path: str) -> bool:
    """
    3a. check if file is a video by extension
    """
    video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.m4v', '.flv'}
    ext = os.path.splitext(path)[1].lower()
    return ext in video_exts


def is_image_file(path: str) -> bool:
    """
    3b. check if file is an image by extension
    """
    image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
    ext = os.path.splitext(path)[1].lower()
    return ext in image_exts


def is_audio_file(path: str) -> bool:
    """
    3c. check if file is audio by extension
    """
    audio_exts = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
    ext = os.path.splitext(path)[1].lower()
    return ext in audio_exts


def get_platform_from_url(url: str) -> str:
    """
    4a. detect platform from video URL
    """
    url_lower = url.lower()
    
    if "tiktok.com" in url_lower:
        return "tiktok"
    elif "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "instagram.com" in url_lower:
        return "instagram"
    elif "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    elif "vimeo.com" in url_lower:
        return "vimeo"
    elif "facebook.com" in url_lower or "fb.watch" in url_lower:
        return "facebook"
    else:
        return "other"


def hex_to_rgb(hex_color: str) -> tuple:
    """
    5a. convert hex color to RGB tuple
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple) -> str:
    """
    5b. convert RGB tuple to hex color
    """
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

"""
Da Editor - Core Module
========================
all the heavy lifting happens here
video processing, scraping, transcription

imports for easy access from other modules
"""

from .downloader import VideoDownloader
from .transcriber import WhisperTranscriber
from .keyword_extractor import KeywordExtractor
from .video_creator import VideoCreator

# pro versions with better quality
try:
    from .image_scraper_pro import ImageScraperPro
    from .video_creator_pro import VideoCreatorPro
except ImportError:
    pass

# safety monitoring
try:
    from .safety_monitor import SafetyMonitor
except ImportError:
    pass

__all__ = [
    "VideoDownloader",
    "WhisperTranscriber", 
    "KeywordExtractor",
    "VideoCreator",
    "ImageScraperPro",
    "VideoCreatorPro",
    "SafetyMonitor"
]

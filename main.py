#!/usr/bin/env python3
"""
Da Editor - Video B-Roll Automation Tool
=========================================
yo this is the main entry point for the whole app frfr
runs the customtkinter gui and kicks off the job processing

1a. handles app initialization
1b. sets up the theme (pink vibes)
1c. connects all the modules together
"""

import os
import sys

# 1a. add the app directory to path so imports work smooth
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

# 1b. gotta check for dependencies before we even start
def check_dependencies():
    """
    make sure we got everything we need installed
    no point in starting if we missing stuff fr
    """
    missing = []
    
    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")
    
    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp")
    
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")
    
    try:
        import requests
    except ImportError:
        missing.append("requests")
    
    if missing:
        print("=" * 50)
        print("YO HOLD UP - Missing these packages:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nRun this to fix it:")
        print(f"  pip install {' '.join(missing)}")
        print("=" * 50)
        return False
    
    return True


def main():
    """
    1c. main entry - fire up the app
    this is where the magic happens no cap
    """
    print("=" * 60)
    print("  DA EDITOR - Video B-Roll Automation")
    print("  making content creation ez since 2024")
    print("=" * 60)
    
    # check we got everything first
    if not check_dependencies():
        sys.exit(1)
    
    # 2a. now we can import the actual app
    from ui.app import DaEditorApp
    
    # 2b. run it
    app = DaEditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()

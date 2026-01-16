#!/usr/bin/env python3
"""
Da Editor - Setup Script
=========================
one-click setup for the whole app
installs python deps, playwright browsers, and preps everything

just run: python setup.py
"""

import os
import sys
import subprocess
import platform


def print_header(text):
    """print a fancy header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def run_command(cmd, description):
    """run a command and show status"""
    print(f"  [{description}]...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    done")
            return True
        else:
            print(f"    failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"    error: {e}")
        return False


def main():
    print_header("DA EDITOR SETUP")
    print("this gonna set up everything you need to run the app")
    print("sit tight this might take a minute...\n")
    
    # check python version
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 8):
        print("ERROR: Need Python 3.8 or higher")
        sys.exit(1)
    
    # 1. install python dependencies
    print_header("Installing Python packages")
    
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(requirements_path):
        run_command(f'"{sys.executable}" -m pip install --upgrade pip', "Upgrading pip")
        run_command(f'"{sys.executable}" -m pip install -r "{requirements_path}"', "Installing requirements")
    else:
        print("  requirements.txt not found, skipping")
    
    # 2. install playwright browsers
    print_header("Installing Playwright browsers")
    run_command(f'"{sys.executable}" -m playwright install chromium', "Installing Chromium")
    
    # 3. download spacy model for keyword extraction
    print_header("Installing spaCy language model")
    run_command(f'"{sys.executable}" -m spacy download en_core_web_sm', "Downloading en_core_web_sm")
    
    # 4. check for ffmpeg
    print_header("Checking FFmpeg")
    result = subprocess.run("ffmpeg -version", shell=True, capture_output=True)
    if result.returncode == 0:
        print("  ffmpeg is installed")
    else:
        print("  WARNING: ffmpeg not found!")
        print("  Please install ffmpeg:")
        if platform.system() == "Windows":
            print("    - Download from https://ffmpeg.org/download.html")
            print("    - Or: winget install ffmpeg")
        elif platform.system() == "Darwin":
            print("    - brew install ffmpeg")
        else:
            print("    - sudo apt install ffmpeg")
    
    # 5. check for node.js (for electron)
    print_header("Checking Node.js")
    result = subprocess.run("node --version", shell=True, capture_output=True)
    if result.returncode == 0:
        version = result.stdout.decode().strip()
        print(f"  Node.js version: {version}")
    else:
        print("  WARNING: Node.js not found!")
        print("  Please install Node.js 18+ for the Electron app")
        print("  Download from: https://nodejs.org/")
    
    # 6. setup electron (if node exists)
    electron_dir = os.path.join(os.path.dirname(__file__), "electron")
    if os.path.exists(electron_dir) and result.returncode == 0:
        print_header("Setting up Electron app")
        os.chdir(electron_dir)
        run_command("npm install", "Installing npm packages")
        os.chdir(os.path.dirname(__file__))
    
    # done
    print_header("SETUP COMPLETE")
    print("You're all set! Here's how to run the app:\n")
    print("  Option 1 (Electron app):")
    print("    cd electron && npm run dev")
    print()
    print("  Option 2 (Python GUI):")
    print("    python main.py")
    print()
    print("  Option 3 (CLI):")
    print("    python -m core.job_runner --job-folder /path/to/job --settings '{}'")
    print()
    print("enjoy! - the da editor team")


if __name__ == "__main__":
    main()


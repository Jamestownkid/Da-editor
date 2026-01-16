#!/bin/bash
# DA EDITOR - ONE CLICK INSTALLER
# ================================
# just paste this in your terminal and it handles everything
# no file system knowledge needed fr

set -e

echo ""
echo "========================================"
echo "   DA EDITOR - INSTALLING..."
echo "========================================"
echo ""

# go to downloads folder (standard location)
cd ~/Downloads 2>/dev/null || cd ~

# clone or update repo
if [ -d "Da-editor" ]; then
    echo "[+] Found existing install, updating..."
    cd Da-editor
    git pull origin main 2>/dev/null || true
else
    echo "[+] Downloading Da Editor..."
    git clone https://github.com/Jamestownkid/Da-editor.git
    cd Da-editor
fi

echo "[+] Installing Python dependencies..."
pip install -r requirements.txt --quiet 2>/dev/null || pip3 install -r requirements.txt --quiet

echo "[+] Installing Playwright browser..."
playwright install chromium 2>/dev/null || python3 -m playwright install chromium 2>/dev/null || true

echo "[+] Checking for FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "!!! FFmpeg not found !!!"
    echo "Install it:"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  Mac: brew install ffmpeg"
    echo ""
fi

echo "[+] Setting up Electron app..."
cd electron
npm install --silent 2>/dev/null || true

echo ""
echo "========================================"
echo "   INSTALL COMPLETE!"
echo "========================================"
echo ""
echo "To open the app, run:"
echo "  cd ~/Downloads/Da-editor && ./open.sh"
echo ""


# Da Editor - Installation Guide

## First Time Install

### 1. Clone the repo
```bash
git clone https://github.com/Jamestownkid/Da-editor.git
cd Da-editor
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Playwright browsers
```bash
playwright install chromium
```

### 4. Install FFmpeg (required for video rendering)

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH

### 5. Download Whisper model (first run will be slow otherwise)
```bash
python3 -c "import whisper; whisper.load_model('medium')"
```

### 6. (Optional) Install Electron UI dependencies
```bash
cd electron
npm install
```

### 7. Run the app
```bash
# Python backend only
python3 main.py

# OR with Electron UI (dev mode)
cd electron && npm run dev
```

---

## Update from GitHub

```bash
cd Da-editor
git pull origin main
pip install -r requirements.txt --upgrade
```

---

## Push changes to GitHub

```bash
cd Da-editor
git add .
git commit -m "your commit message"
git push origin main
```

---

## Quick Test

```bash
python3 test_real.py
```

This will download test videos and create all 3 outputs.

---

## Troubleshooting

### "ffmpeg not found"
Make sure ffmpeg is installed and in your PATH. Run `ffmpeg -version` to check.

### "yt-dlp errors"
Update yt-dlp: `pip install --upgrade yt-dlp`

### "Playwright errors"
Run: `playwright install chromium`

### "CUDA out of memory"
Set `useGpu: false` in settings, or use a smaller Whisper model.


# Da Editor - Video B-Roll Automation Tool

Turn your video links into fire content with automated B-roll generation.

![Da Editor](assets/icons/app_icon.svg)

## What It Does

Da Editor takes YouTube, TikTok, and Instagram links and creates three professional video outputs:

1. **Landscape B-Roll** (16:9) - Slideshow with Ken Burns effect + sound effects
2. **Portrait Split** (9:16) - For TikTok/Reels with white space at bottom for your face
3. **YouTube Mix** - Scrambled montage clips from YouTube videos (muted)

## Features

- Download videos from YouTube, TikTok, Instagram (anything yt-dlp supports)
- Generate subtitles using Whisper AI
- Extract keywords from subtitles for image search
- Scrape high-quality images with Playwright + Puppeteer
- Create videos with Ken Burns zoom/pan effects
- Add sound effects between image transitions (ching sounds prioritized)
- Job queue system that processes one at a time
- Resume from crashes - jobs persist to disk
- System safety checks (disk, RAM, CPU)
- Pink minimalist UI because we fancy

## Installation

### One-Click Install (Recommended)

**Linux/Mac:**
```bash
# paste this in your terminal
curl -sSL https://raw.githubusercontent.com/Jamestownkid/Da-editor/main/install.sh | bash
```

Or if you downloaded the zip:
```bash
cd ~/Downloads/Da-editor
chmod +x install.sh open.sh update.sh
./install.sh
```

**Windows:**
1. Download the zip from GitHub
2. Extract to your Downloads folder
3. Double-click `install.bat` (coming soon)
4. Or run: `cd %USERPROFILE%\Downloads\Da-editor && npm install && cd electron && npm run dev`

### Manual Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install FFmpeg
# Ubuntu/Debian: sudo apt install ffmpeg
# Mac: brew install ffmpeg
# Windows: winget install ffmpeg

# Install Playwright browsers
playwright install chromium

# Install Node.js dependencies (for Electron UI)
cd electron && npm install
```

### Requirements

- Python 3.8+
- Node.js 18+ (for Electron UI)
- FFmpeg (for video processing)
- ~10GB disk space for Whisper models

## Usage

### Opening the App

**After first install:**
```bash
cd ~/Downloads/Da-editor && ./open.sh
```

**To update and open:**
```bash
cd ~/Downloads/Da-editor && ./update.sh
```

### What You'll See

1. Pink minimalist desktop app opens
2. Paste your video links in the main area
3. Click [SRT] button next to links you want transcribed
4. Click [IMG] button next to links you want images from
5. Set your job name and output folder
6. Click Start Job
7. Watch the magic happen
8. Three videos appear in your job folder

## How It Works

1. **Paste Links** - Drop your YouTube/TikTok/Instagram URLs
2. **Create Job** - Click Start to create a job folder with all assets
3. **Download** - Videos are downloaded via yt-dlp
4. **Transcribe** - Whisper generates SRT subtitles
5. **Keywords** - NLP extracts searchable terms from subtitles
6. **Scrape** - Images are gathered from the web (Playwright)
7. **Render** - FFmpeg creates the three video outputs

## Project Structure

```
da_editor/
├── electron/           # Electron + React + TypeScript UI
│   ├── src/           # React components
│   └── electron/      # Main process
├── core/              # Python processing modules
│   ├── downloader.py  # yt-dlp wrapper
│   ├── transcriber.py # Whisper integration
│   ├── image_scraper_pro.py  # Image scraping
│   └── video_creator_pro.py  # Video rendering
├── assets/
│   ├── icons/         # App icons
│   └── sounds/        # Sound effects
├── ui/                # Legacy Python GUI
└── utils/             # Helper functions
```

## Settings

All settings are in the Settings panel:

- **Whisper Model** - tiny/base/small/medium/large (default: medium)
- **GPU Mode** - Use CUDA for faster transcription
- **Sounds Folder** - Custom sound effects
- **Background Color** - Default white, customizable
- **Seconds Per Image** - How long each image shows
- **Minimum Images** - Target image count for scraping (default: 20)

## Job Folder Structure

Each job creates:
```
MyJob/
├── job.json           # Job state and settings
├── images/            # Scraped images
├── image_manifest.json # Tracks used images
├── links.txt          # Your links with markers
├── errors.log         # Any errors
├── output_video.mp4   # Landscape output
├── broll_instagram_*.mp4  # Portrait output
└── broll_youtube_*.mp4    # YouTube mix output
```

## Troubleshooting

**FFmpeg not found**
- Windows: `winget install ffmpeg`
- Mac: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

**Playwright browsers not installed**
```bash
playwright install chromium
```

**Whisper out of memory**
- Use a smaller model (tiny/base)
- Disable GPU mode
- Close other applications

**Scraping not working**
- Some sites block automated requests
- The app uses multiple fallback methods
- Results may vary by region

**App won't open**
```bash
cd electron && npm install && npm run build && npm run dev
```

## License

MIT - do whatever you want with it

## Credits

Built with:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video downloading
- [OpenAI Whisper](https://github.com/openai/whisper) - Transcription
- [Playwright](https://playwright.dev/) - Browser automation
- [FFmpeg](https://ffmpeg.org/) - Video processing
- [Electron](https://electronjs.org/) - Desktop app framework
- [React](https://react.dev/) - UI components
- [Tailwind CSS](https://tailwindcss.com/) - Styling

---

made with love by jamestownkid

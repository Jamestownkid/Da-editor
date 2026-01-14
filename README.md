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
- Add sound effects between image transitions
- Job queue system that processes one at a time
- Resume from crashes - jobs persist to disk
- System safety checks (disk, RAM, CPU)
- Pink minimalist UI because we fancy

## Installation

### Quick Setup (Recommended)

```bash
# 1. Clone or download the repo
git clone https://github.com/Jamestownkid/Da-editor.git
cd Da-editor

# 2. Run the setup script
python setup.py

# 3. Run the app
cd electron && npm run dev
```

### Manual Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium

# Install spaCy language model
python -m spacy download en_core_web_sm

# Install Node.js dependencies (for Electron UI)
cd electron && npm install
```

### Requirements

- Python 3.8+
- Node.js 18+ (for Electron UI)
- FFmpeg (for video processing)
- ~10GB disk space for Whisper models

## Usage

### Desktop App (Electron)

```bash
cd electron
npm run dev
```

### Python CLI

```bash
python main.py
```

### CLI Mode

```bash
python -m core.job_runner --job-folder /path/to/job --settings '{"whisperModel": "base"}'
```

## How It Works

1. **Paste Links** - Drop your YouTube/TikTok/Instagram URLs
2. **Create Job** - Click Start to create a job folder with all assets
3. **Download** - Videos are downloaded via yt-dlp
4. **Transcribe** - Whisper generates SRT subtitles
5. **Keywords** - NLP extracts searchable terms from subtitles
6. **Scrape** - Images are gathered from the web (Playwright + Puppeteer)
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

- **Whisper Model** - tiny/base/small/medium/large
- **GPU Mode** - Use CUDA for faster transcription
- **Sounds Folder** - Custom sound effects
- **Background Color** - Default white, customizable
- **Seconds Per Image** - How long each image shows
- **Minimum Images** - Target image count for scraping

## Job Folder Structure

Each job creates:
```
MyJob/
├── job.json           # Job state and settings
├── downloads/         # Downloaded videos
├── srt/               # Generated subtitles
├── images/            # Scraped images
├── renders/           # Final video outputs
├── logs/              # Processing logs
└── cache/             # Temp files
```

## Troubleshooting

**FFmpeg not found**
- Windows: `winget install ffmpeg`
- Mac: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

**Playwright browsers not installed**
```bash
python -m playwright install chromium
```

**Whisper out of memory**
- Use a smaller model (tiny/base)
- Disable GPU mode
- Close other applications

**Scraping not working**
- Some sites block automated requests
- The app uses multiple fallback methods
- Results may vary by region

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

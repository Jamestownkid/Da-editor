/**
 * Da Editor - TypeScript Types (v2)
 * ===================================
 * updated types matching the expected structure
 * with per-link SRT/IMG toggles
 */

// job status
export type JobStatus = 'pending' | 'running' | 'done' | 'error' | 'paused'

// video platform
export type Platform = 'youtube' | 'tiktok' | 'instagram' | 'twitter' | 'other'

// settings object
export interface Settings {
  outputFolder: string
  whisperModel: 'small' | 'medium' | 'large'  // rule 31
  useGpu: boolean  // rule 32
  bgColor: string  // rules 47-48
  bgVideo?: string  // rule 48
  soundsFolder: string
  secondsPerImage: number
  soundVolume: number  // rule 42
  minImages: number
  deleteAfterUse?: boolean  // rule 69
  minImageWidth?: number  // image quality
  minImageHeight?: number  // image quality
}

// per-link data with SRT/IMG toggles (rule 5)
export interface LinkItem {
  url: string
  srt: boolean  // generate SRT for this link
  images: boolean  // scrape images from SRT keywords
  downloaded_path?: string
  srt_path?: string
  platform?: Platform
  deleted?: boolean  // rule 70
}

// downloaded video info
export interface DownloadedVideo {
  url: string
  path: string
  platform: Platform
  title?: string
  duration?: number
}

// job object matching the sample structure
export interface Job {
  id: string
  topic?: string
  folder?: string
  created: string
  created_at?: string
  urls?: LinkItem[]  // new format with per-link toggles
  links?: (string | LinkItem)[]  // backwards compat
  generateSrt?: boolean  // legacy
  downloadVideos?: boolean  // legacy
  status: JobStatus
  progress: number
  outputs: {
    slideshow?: string | null
    portrait?: string | null
    youtubeMix?: string | null
    landscape?: string | null
    youtube_mix?: string | null
  }
  settings?: Settings | null
  errors: string[]
  downloadedVideos?: DownloadedVideo[]
  srtFiles?: string[]
  keywords?: string[]
  images?: string[]
  lastUpdated?: string
  last_updated?: string
  checkpoint?: string
}

// scraper result
export interface ScrapedImage {
  url: string
  localPath: string
  keyword: string
  width: number
  height: number
  hash?: string
}

// system check result
export interface SystemCheck {
  safe: boolean
  disk: 'OK' | 'LOW' | 'CRITICAL'
  memory: 'OK' | 'LOW' | 'CRITICAL'
  cpu: 'OK' | 'HIGH' | 'CRITICAL'
  gpu?: {
    available: boolean
    name?: string
    vram?: number
  }
}

// whisper model status (rule 29)
export interface WhisperStatus {
  small: boolean
  medium: boolean
  large: boolean
}

// image manifest for deduplication (rule 88)
export interface ImageManifest {
  used_hashes: string[]
  used_urls: string[]
  images: string[]
}

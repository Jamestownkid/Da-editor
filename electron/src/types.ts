/**
 * Da Editor - TypeScript Types
 * ==============================
 * all the types we use throughout the app
 * keeping it typed so we dont mess up
 */

// 1a. job status - where the job at in the pipeline
export type JobStatus = 'pending' | 'running' | 'done' | 'error' | 'paused'

// 1b. video platform - where the link from
export type Platform = 'youtube' | 'tiktok' | 'instagram' | 'twitter' | 'other'

// 2a. settings object - all user preferences
export interface Settings {
  outputFolder: string
  whisperModel: 'tiny' | 'base' | 'small' | 'medium' | 'large'
  useGpu: boolean
  bgColor: string
  bgVideo?: string
  soundsFolder: string
  secondsPerImage: number
  soundVolume: number
  minImages: number
  deleteAfterUse?: boolean
}

// 2b. downloaded video info
export interface DownloadedVideo {
  url: string
  path: string
  platform: Platform
  title?: string
  duration?: number
}

// 3a. job object - the main thing we tracking
export interface Job {
  id: string
  folder: string
  created: string
  links: string[]
  generateSrt: boolean
  downloadVideos: boolean
  status: JobStatus
  progress: number
  outputs: {
    slideshow: string | null
    portrait: string | null
    youtubeMix: string | null
  }
  settings: Settings | null
  errors: string[]
  downloadedVideos: DownloadedVideo[]
  srtFiles: string[]
  keywords: string[]
  images: string[]
  lastUpdated?: string
  checkpoint?: string
}

// 3b. scraper result - what we get from image scraping
export interface ScrapedImage {
  url: string
  localPath: string
  keyword: string
  width: number
  height: number
  hash?: string
}

// 4a. system check result
export interface SystemCheck {
  safe: boolean
  disk: 'OK' | 'LOW' | 'CRITICAL'
  memory: 'OK' | 'LOW' | 'CRITICAL'
  cpu: 'OK' | 'HIGH'
  gpu?: {
    available: boolean
    name?: string
    vram?: number
  }
}

// 4b. whisper model status
export interface WhisperStatus {
  tiny: boolean
  base: boolean
  small: boolean
  medium: boolean
  large: boolean
}


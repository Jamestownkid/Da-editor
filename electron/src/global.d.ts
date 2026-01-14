/**
 * Da Editor - Global Type Declarations
 * =====================================
 * extends Window interface to include electronAPI
 */

import { Job, Settings } from './types'

declare global {
  interface Window {
    electronAPI: {
      getSettings: () => Promise<Settings | null>
      saveSettings: (settings: Settings) => Promise<boolean>
      selectFolder: () => Promise<string | null>
      selectFile: (filters?: Array<{ name: string; extensions: string[] }>) => Promise<string | null>
      openFolder: (path: string) => Promise<boolean>
      scanJobs: (rootFolder: string) => Promise<Job[]>
      createJobFolder: (root: string, name: string) => Promise<string>
      saveJob: (folder: string, data: Job) => Promise<boolean>
      readJob: (folder: string) => Promise<Job | null>
      runJob: (folder: string, settings: Settings) => Promise<{ success: boolean }>
      stopJob: () => Promise<boolean>
      checkSystem: () => Promise<{
        safe: boolean
        disk: 'OK' | 'LOW' | 'CRITICAL'
        memory: 'OK' | 'LOW' | 'CRITICAL'
        cpu: 'OK' | 'HIGH' | 'CRITICAL'
        gpu?: { available: boolean; name?: string; vram?: number }
      }>
      checkPythonDeps: () => Promise<{ installed: boolean; python: string | null }>
      scanWhisper: () => Promise<Record<string, boolean>>
      onJobProgress: (callback: (msg: string) => void) => void
      onJobError: (callback: (msg: string) => void) => void
      removeJobListeners: () => void
    }
  }
}

export {}


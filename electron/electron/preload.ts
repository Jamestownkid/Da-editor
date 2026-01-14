/**
 * Da Editor - Preload Script (v2)
 * ================================
 * bridge between renderer and main process
 * keeps things secure with context isolation
 * 
 * FIXED: added ffmpeg check, gpu check, download-whisper
 */

import { contextBridge, ipcRenderer } from 'electron'

// expose electron APIs to the renderer process safely
contextBridge.exposeInMainWorld('electronAPI', {
  // settings
  getSettings: () => ipcRenderer.invoke('get-settings'),
  saveSettings: (settings: any) => ipcRenderer.invoke('save-settings', settings),
  
  // dialogs
  selectFolder: () => ipcRenderer.invoke('select-folder'),
  selectFile: (filters?: any[]) => ipcRenderer.invoke('select-file', filters),
  openFolder: (path: string) => ipcRenderer.invoke('open-folder', path),
  
  // jobs
  scanJobs: (rootFolder: string) => ipcRenderer.invoke('scan-jobs', rootFolder),
  createJobFolder: (root: string, name: string) => ipcRenderer.invoke('create-job-folder', root, name),
  saveJob: (folder: string, data: any) => ipcRenderer.invoke('save-job', folder, data),
  readJob: (folder: string) => ipcRenderer.invoke('read-job', folder),
  
  // job execution
  runJob: (folder: string, settings: any) => ipcRenderer.invoke('run-job', folder, settings),
  stopJob: () => ipcRenderer.invoke('stop-job'),
  
  // system checks - FIXED
  checkSystem: () => ipcRenderer.invoke('check-system'),
  checkFfmpeg: () => ipcRenderer.invoke('check-ffmpeg'),
  checkPythonDeps: () => ipcRenderer.invoke('check-python-deps'),
  checkGpu: () => ipcRenderer.invoke('check-gpu'),
  scanWhisper: () => ipcRenderer.invoke('scan-whisper'),
  downloadWhisper: (model: string) => ipcRenderer.invoke('download-whisper', model),
  getSystemStats: () => ipcRenderer.invoke('get-system-stats'),
  
  // notes feature
  saveNotes: (folder: string, notes: string) => ipcRenderer.invoke('save-notes', folder, notes),
  readNotes: (folder: string) => ipcRenderer.invoke('read-notes', folder),
  
  // window controls
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  maximizeWindow: () => ipcRenderer.invoke('maximize-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),
  
  // event listeners for job progress
  onJobProgress: (callback: (msg: string) => void) => {
    ipcRenderer.on('job-progress', (_, msg) => callback(msg))
  },
  onJobError: (callback: (msg: string) => void) => {
    ipcRenderer.on('job-error', (_, msg) => callback(msg))
  },
  
  // remove listeners
  removeJobListeners: () => {
    ipcRenderer.removeAllListeners('job-progress')
    ipcRenderer.removeAllListeners('job-error')
  }
})

// type declarations for typescript
declare global {
  interface Window {
    electronAPI: {
      getSettings: () => Promise<any>
      saveSettings: (settings: any) => Promise<boolean>
      selectFolder: () => Promise<string | null>
      selectFile: (filters?: any[]) => Promise<string | null>
      openFolder: (path: string) => Promise<boolean>
      scanJobs: (rootFolder: string) => Promise<any[]>
      createJobFolder: (root: string, name: string) => Promise<string>
      saveJob: (folder: string, data: any) => Promise<boolean>
      readJob: (folder: string) => Promise<any | null>
      runJob: (folder: string, settings: any) => Promise<{ success: boolean }>
      stopJob: () => Promise<boolean>
      checkSystem: () => Promise<any>
      checkFfmpeg: () => Promise<{ ffmpeg: boolean; ffprobe: boolean; message: string }>
      checkPythonDeps: () => Promise<{ installed: boolean; python: string | null; missing?: string[] }>
      checkGpu: () => Promise<{ cuda: boolean; device: string; vram: number }>
      scanWhisper: () => Promise<Record<string, boolean>>
      downloadWhisper: (model: string) => Promise<{ success: boolean; output?: string }>
      minimizeWindow: () => Promise<void>
      maximizeWindow: () => Promise<void>
      closeWindow: () => Promise<void>
      onJobProgress: (callback: (msg: string) => void) => void
      onJobError: (callback: (msg: string) => void) => void
      removeJobListeners: () => void
    }
  }
}

/**
 * Da Editor - Preload Script
 * ===========================
 * this is the bridge between renderer and main process
 * keeps things secure with context isolation
 * 
 * exposing only what we need to the frontend
 */

import { contextBridge, ipcRenderer } from 'electron'

// 1a. expose electron APIs to the renderer process safely
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
  
  // system checks
  checkSystem: () => ipcRenderer.invoke('check-system'),
  checkPythonDeps: () => ipcRenderer.invoke('check-python-deps'),
  scanWhisper: () => ipcRenderer.invoke('scan-whisper'),
  
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

// 1b. type declarations for typescript
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
      checkPythonDeps: () => Promise<{ installed: boolean; python: string | null }>
      scanWhisper: () => Promise<Record<string, boolean>>
      onJobProgress: (callback: (msg: string) => void) => void
      onJobError: (callback: (msg: string) => void) => void
      removeJobListeners: () => void
    }
  }
}


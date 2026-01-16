/**
 * Da Editor - Electron Main Process (v2)
 * ======================================
 * handles window creation, IPC, and talking to the python backend
 * 
 * FIXED:
 * - proper python deps check (not moviepy - we dont use that)
 * - ffmpeg/ffprobe gate so users know if its missing
 * - job folder path in scan results
 * - better error handling
 */

import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron'
import { spawn, ChildProcess, execSync } from 'child_process'
import * as path from 'path'
import * as fs from 'fs'

// use a simple JSON file for settings instead of electron-store
// electron-store v8 has ESM issues that cause crashes
const settingsPath = path.join(app.getPath('userData'), 'settings.json')

const defaultSettings = {
  outputFolder: '',
  whisperModel: 'medium',  // default to medium per user request
  useGpu: true,
  bgColor: '#FFFFFF',
  soundsFolder: '',
  secondsPerImage: 4.0,
  soundVolume: 0.8,
  minImages: 15,
  deleteAfterUse: false
}

// simple store implementation that doesn't crash
const store = {
  store: defaultSettings as Record<string, unknown>,
  
  load() {
    try {
      if (fs.existsSync(settingsPath)) {
        const data = JSON.parse(fs.readFileSync(settingsPath, 'utf-8'))
        this.store = { ...defaultSettings, ...data }
      } else {
        // set default output folder now that app is ready
        this.store = { 
          ...defaultSettings, 
          outputFolder: path.join(app.getPath('documents'), 'DaEditor_Output')
        }
        this.save()
      }
    } catch (e) {
      console.error('failed to load settings:', e)
      this.store = { ...defaultSettings }
    }
  },
  
  save() {
    try {
      fs.writeFileSync(settingsPath, JSON.stringify(this.store, null, 2))
    } catch (e) {
      console.error('failed to save settings:', e)
    }
  },
  
  get(key: string) {
    return this.store[key]
  },
  
  set(key: string, value: unknown) {
    this.store[key] = value
    this.save()
  }
}

let mainWindow: BrowserWindow | null = null
let pythonProcess: ChildProcess | null = null

// figure out where we at in the filesystem
const isDev = !app.isPackaged
const rootPath = isDev 
  ? path.join(__dirname, '..', '..') 
  : path.join(process.resourcesPath)

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    backgroundColor: '#0d0d14',
    titleBarStyle: 'hiddenInset',
    frame: process.platform === 'darwin' ? true : false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(rootPath, 'assets', 'icons', 'app_icon.png'),
    show: false
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    if (pythonProcess) {
      pythonProcess.kill()
      pythonProcess = null
    }
  })
}

// ============================================
// IPC HANDLERS
// ============================================

// window controls
ipcMain.handle('minimize-window', () => {
  mainWindow?.minimize()
})

ipcMain.handle('maximize-window', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize()
  } else {
    mainWindow?.maximize()
  }
})

ipcMain.handle('close-window', () => {
  mainWindow?.close()
})

// get settings
ipcMain.handle('get-settings', () => {
  return store.store
})

// save settings  
ipcMain.handle('save-settings', (_, settings) => {
  Object.keys(settings).forEach(key => {
    store.set(key, settings[key])
  })
  return true
})

// select folder dialog
ipcMain.handle('select-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openDirectory', 'createDirectory']
  })
  return result.canceled ? null : result.filePaths[0]
})

// select file dialog
ipcMain.handle('select-file', async (_, filters) => {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openFile'],
    filters: filters || [{ name: 'All Files', extensions: ['*'] }]
  })
  return result.canceled ? null : result.filePaths[0]
})

// open folder in file manager
ipcMain.handle('open-folder', async (_, folderPath) => {
  if (fs.existsSync(folderPath)) {
    shell.openPath(folderPath)
    return true
  }
  return false
})

// scan for existing jobs - FIXED: includes folder path
ipcMain.handle('scan-jobs', async (_, rootFolder) => {
  const jobs: any[] = []
  
  if (!fs.existsSync(rootFolder)) {
    return jobs
  }
  
  const folders = fs.readdirSync(rootFolder)
  
  for (const folder of folders) {
    const folderPath = path.join(rootFolder, folder)
    const jsonPath = path.join(folderPath, 'job.json')
    
    if (fs.existsSync(jsonPath)) {
      try {
        const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'))
        // FIXED: attach folder path so UI can reference it
        data.jobFolder = folderPath
        data.folderName = folder
        jobs.push(data)
      } catch (e) {
        console.log(`couldnt load ${jsonPath}: ${e}`)
      }
    }
  }
  
  return jobs
})

// create job folder structure
ipcMain.handle('create-job-folder', async (_, rootFolder, jobName) => {
  const jobFolder = path.join(rootFolder, jobName)
  
  // create the job folder and subfolders
  const subfolders = ['images']  // simplified - we put videos/srt in root
  
  if (!fs.existsSync(jobFolder)) {
    fs.mkdirSync(jobFolder, { recursive: true })
  }
  
  for (const sub of subfolders) {
    const subPath = path.join(jobFolder, sub)
    if (!fs.existsSync(subPath)) {
      fs.mkdirSync(subPath, { recursive: true })
    }
  }
  
  return jobFolder
})

// save job json
ipcMain.handle('save-job', async (_, jobFolder, jobData) => {
  const jsonPath = path.join(jobFolder, 'job.json')
  fs.writeFileSync(jsonPath, JSON.stringify(jobData, null, 2))
  return true
})

// read job json
ipcMain.handle('read-job', async (_, jobFolder) => {
  const jsonPath = path.join(jobFolder, 'job.json')
  if (fs.existsSync(jsonPath)) {
    return JSON.parse(fs.readFileSync(jsonPath, 'utf-8'))
  }
  return null
})

// DELETE JOB FOLDER - removes entire job directory
ipcMain.handle('delete-folder', async (_, folderPath) => {
  try {
    if (fs.existsSync(folderPath)) {
      fs.rmSync(folderPath, { recursive: true, force: true })
      return true
    }
    return false
  } catch (e) {
    console.error('failed to delete folder:', e)
    return false
  }
})

// ============================================
// SYSTEM CHECKS - FIXED
// ============================================

// check ffmpeg and ffprobe - CRITICAL
ipcMain.handle('check-ffmpeg', async () => {
  const result = { ffmpeg: false, ffprobe: false, message: '' }
  
  try {
    execSync('ffmpeg -version', { stdio: 'pipe' })
    result.ffmpeg = true
  } catch {
    result.message = 'ffmpeg not found. '
  }
  
  try {
    execSync('ffprobe -version', { stdio: 'pipe' })
    result.ffprobe = true
  } catch {
    result.message += 'ffprobe not found. '
  }
  
  if (!result.ffmpeg || !result.ffprobe) {
    result.message += 'Install ffmpeg: https://ffmpeg.org/download.html'
  }
  
  return result
})

// check python dependencies - FIXED: check what we actually use
ipcMain.handle('check-python-deps', async () => {
  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
    
    // check the ACTUAL deps we use (not moviepy)
    const checkScript = `
import sys
missing = []
try:
    import yt_dlp
except ImportError:
    missing.append('yt-dlp')
try:
    from PIL import Image
except ImportError:
    missing.append('pillow')
try:
    import requests
except ImportError:
    missing.append('requests')
try:
    import whisper
except ImportError:
    missing.append('openai-whisper')

# optional but recommended
optional_missing = []
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    optional_missing.append('playwright')
try:
    import torch
except ImportError:
    optional_missing.append('torch')

if missing:
    print(f"MISSING:{','.join(missing)}")
elif optional_missing:
    print(f"OPTIONAL:{','.join(optional_missing)}")
else:
    print("OK")
`
    
    const check = spawn(pythonCmd, ['-c', checkScript])
    
    let output = ''
    check.stdout?.on('data', (d) => { output += d.toString() })
    check.stderr?.on('data', (d) => { output += d.toString() })
    
    check.on('close', (code) => {
      output = output.trim()
      
      if (output.startsWith('MISSING:')) {
        resolve({
          installed: false,
          missing: output.replace('MISSING:', '').split(','),
          python: pythonCmd
        })
      } else if (output.startsWith('OPTIONAL:')) {
        resolve({
          installed: true,
          optionalMissing: output.replace('OPTIONAL:', '').split(','),
          python: pythonCmd
        })
      } else if (output === 'OK' || code === 0) {
        resolve({
          installed: true,
          python: pythonCmd
        })
      } else {
        resolve({ installed: false, python: pythonCmd, error: output })
      }
    })
    
    check.on('error', () => {
      resolve({ installed: false, python: null, error: 'Python not found' })
    })
  })
})

// check GPU availability
ipcMain.handle('check-gpu', async () => {
  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
    const script = `
import json
result = {"cuda": False, "device": "cpu", "vram": 0}
try:
    import torch
    if torch.cuda.is_available():
        result["cuda"] = True
        result["device"] = torch.cuda.get_device_name(0)
        result["vram"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1)
except:
    pass
print(json.dumps(result))
`
    const check = spawn(pythonCmd, ['-c', script])
    
    let output = ''
    check.stdout?.on('data', (d) => { output += d.toString() })
    
    check.on('close', () => {
      try {
        resolve(JSON.parse(output.trim()))
      } catch {
        resolve({ cuda: false, device: 'cpu', vram: 0 })
      }
    })
    
    check.on('error', () => resolve({ cuda: false, device: 'cpu', vram: 0 }))
  })
})

// scan for whisper models
ipcMain.handle('scan-whisper', async () => {
  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
    const script = `
import os, json
cache = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
models = {}
for m in ["tiny", "base", "small", "medium", "large"]:
    f = os.path.join(cache, f"{m}.pt")
    models[m] = os.path.exists(f)
print(json.dumps(models))
`
    const check = spawn(pythonCmd, ['-c', script])
    
    let output = ''
    check.stdout?.on('data', (d) => { output += d.toString() })
    
    check.on('close', () => {
      try {
        resolve(JSON.parse(output.trim()))
      } catch {
        resolve({})
      }
    })
    
    check.on('error', () => resolve({}))
  })
})

// download whisper model
ipcMain.handle('download-whisper', async (_, model: string) => {
  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
    const script = `
import whisper
print("Downloading ${model}...")
whisper.load_model("${model}")
print("Done")
`
    const proc = spawn(pythonCmd, ['-c', script])
    
    let output = ''
    proc.stdout?.on('data', (d) => { 
      const msg = d.toString()
      output += msg
      mainWindow?.webContents.send('job-progress', msg.trim())
    })
    proc.stderr?.on('data', (d) => { 
      mainWindow?.webContents.send('job-progress', d.toString().trim())
    })
    
    proc.on('close', (code) => {
      resolve({ success: code === 0, output })
    })
    
    proc.on('error', (err) => {
      resolve({ success: false, error: err.message })
    })
  })
})

// ============================================
// JOB EXECUTION
// ============================================

// run python job processor
ipcMain.handle('run-job', async (_, jobFolder, settings) => {
  return new Promise((resolve, reject) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
    const scriptPath = path.join(rootPath, 'core', 'job_runner.py')
    
    // spawn python process
    pythonProcess = spawn(pythonCmd, [
      scriptPath,
      '--job-folder', jobFolder,
      '--settings', JSON.stringify(settings)
    ], {
      cwd: rootPath,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1'  // force unbuffered output
      }
    })
    
    // stream output to renderer
    pythonProcess.stdout?.on('data', (data) => {
      const lines = data.toString().split('\n').filter((l: string) => l.trim())
      for (const line of lines) {
        mainWindow?.webContents.send('job-progress', line)
      }
    })
    
    pythonProcess.stderr?.on('data', (data) => {
      const lines = data.toString().split('\n').filter((l: string) => l.trim())
      for (const line of lines) {
        mainWindow?.webContents.send('job-error', line)
      }
    })
    
    pythonProcess.on('close', (code) => {
      pythonProcess = null
      if (code === 0) {
        resolve({ success: true })
      } else {
        reject(new Error(`Job failed with code ${code}`))
      }
    })
    
    pythonProcess.on('error', (err) => {
      pythonProcess = null
      reject(err)
    })
  })
})

// stop current job
ipcMain.handle('stop-job', async () => {
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM')
    pythonProcess = null
    return true
  }
  return false
})

// GET SYSTEM STATS - for real-time monitoring during processing
ipcMain.handle('get-system-stats', async () => {
  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
    const script = `
import json
try:
    import psutil
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    print(json.dumps({
        "cpu": round(cpu),
        "ram": round(mem.percent),
        "disk": round(disk.percent)
    }))
except:
    print(json.dumps({"cpu": 0, "ram": 0, "disk": 0}))
`
    const check = spawn(pythonCmd, ['-c', script])
    
    let output = ''
    check.stdout?.on('data', (d) => { output += d.toString() })
    
    check.on('close', () => {
      try {
        resolve(JSON.parse(output.trim()))
      } catch {
        resolve({ cpu: 0, ram: 0, disk: 0 })
      }
    })
    
    check.on('error', () => {
      resolve({ cpu: 0, ram: 0, disk: 0 })
    })
  })
})

// NOTES FEATURE - save notes.txt for a job
ipcMain.handle('save-notes', async (_, jobFolder, notes) => {
  try {
    const notesPath = path.join(jobFolder, 'notes.txt')
    fs.writeFileSync(notesPath, notes, 'utf-8')
    return true
  } catch (e) {
    console.error('failed to save notes:', e)
    return false
  }
})

// NOTES FEATURE - read notes.txt for a job
ipcMain.handle('read-notes', async (_, jobFolder) => {
  try {
    const notesPath = path.join(jobFolder, 'notes.txt')
    if (fs.existsSync(notesPath)) {
      return fs.readFileSync(notesPath, 'utf-8')
    }
    return ''
  } catch (e) {
    console.error('failed to read notes:', e)
    return ''
  }
})

// check system resources
ipcMain.handle('check-system', async () => {
  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
    const script = `
import json
result = {"safe": True, "disk": "OK", "memory": "OK", "cpu": "OK"}
try:
    import psutil
    # disk check - need at least 5GB
    disk = psutil.disk_usage('/')
    free_gb = disk.free / (1024**3)
    if free_gb < 5:
        result["disk"] = f"LOW ({free_gb:.1f}GB)"
        result["safe"] = False
    # memory check - need at least 2GB available
    mem = psutil.virtual_memory()
    avail_gb = mem.available / (1024**3)
    if avail_gb < 2:
        result["memory"] = f"LOW ({avail_gb:.1f}GB)"
        result["safe"] = False
    # cpu check
    cpu = psutil.cpu_percent(interval=1)
    if cpu > 90:
        result["cpu"] = f"HIGH ({cpu}%)"
except:
    pass
print(json.dumps(result))
`
    const check = spawn(pythonCmd, ['-c', script])
    
    let output = ''
    check.stdout?.on('data', (d) => { output += d.toString() })
    
    check.on('close', () => {
      try {
        resolve(JSON.parse(output.trim()))
      } catch {
        resolve({ safe: true, disk: 'OK', memory: 'OK', cpu: 'OK' })
      }
    })
    
    check.on('error', () => {
      resolve({ safe: true, disk: 'OK', memory: 'OK', cpu: 'OK' })
    })
  })
})

// ============================================
// APP LIFECYCLE
// ============================================

app.whenReady().then(() => {
  // load settings after app is ready
  store.load()
  
  createWindow()
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill()
  }
})

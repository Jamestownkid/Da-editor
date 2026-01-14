/**
 * Da Editor - Electron Main Process
 * ==================================
 * this is where the magic starts yo
 * handles window creation, IPC, and talking to the python backend
 * 
 * we aint playing around with these electron configs
 */

import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron'
import { spawn, ChildProcess } from 'child_process'
import * as path from 'path'
import * as fs from 'fs'
import Store from 'electron-store'

// store for app settings - persists between sessions
const store = new Store({
  defaults: {
    outputFolder: path.join(app.getPath('documents'), 'DaEditor_Output'),
    whisperModel: 'base',
    useGpu: true,
    bgColor: '#FFFFFF',
    soundsFolder: '',
    secondsPerImage: 4.0,
    soundVolume: 0.8,
    minImages: 15
  }
})

let mainWindow: BrowserWindow | null = null
let pythonProcess: ChildProcess | null = null

// figure out where we at in the filesystem
const isDev = !app.isPackaged
const rootPath = isDev 
  ? path.join(__dirname, '..', '..') 
  : path.join(process.resourcesPath)

function createWindow() {
  // 1a. create the main window - make it look fire
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

  // 1b. load the react app
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))
  }

  // 1c. show window when ready - no white flash
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    // kill python if its running
    if (pythonProcess) {
      pythonProcess.kill()
      pythonProcess = null
    }
  })
}

// 2a. IPC handlers - how the renderer talks to us

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

// scan for existing jobs
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
  
  // create all the subfolders we need
  const subfolders = ['downloads', 'srt', 'images', 'renders', 'logs', 'cache']
  
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

// check system resources - make sure we dont nuke the pc
ipcMain.handle('check-system', async () => {
  // we'll get this from python since it has psutil
  return { safe: true, disk: 'OK', memory: 'OK', cpu: 'OK' }
})

// run python job processor
ipcMain.handle('run-job', async (_, jobFolder, settings) => {
  return new Promise((resolve, reject) => {
    // find python executable
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
    const scriptPath = path.join(rootPath, 'core', 'job_runner.py')
    
    // spawn python process
    pythonProcess = spawn(pythonCmd, [
      scriptPath,
      '--job-folder', jobFolder,
      '--settings', JSON.stringify(settings)
    ], {
      cwd: rootPath
    })
    
    // stream output to renderer
    pythonProcess.stdout?.on('data', (data) => {
      const msg = data.toString().trim()
      if (msg) {
        mainWindow?.webContents.send('job-progress', msg)
      }
    })
    
    pythonProcess.stderr?.on('data', (data) => {
      const msg = data.toString().trim()
      if (msg) {
        mainWindow?.webContents.send('job-error', msg)
      }
    })
    
    pythonProcess.on('close', (code) => {
      pythonProcess = null
      if (code === 0) {
        resolve({ success: true })
      } else {
        reject(new Error(`Python process exited with code ${code}`))
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

// check if python dependencies installed
ipcMain.handle('check-python-deps', async () => {
  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
    const check = spawn(pythonCmd, ['-c', 'import yt_dlp, moviepy, PIL; print("OK")'])
    
    let output = ''
    check.stdout?.on('data', (d) => { output += d.toString() })
    
    check.on('close', (code) => {
      resolve({
        installed: code === 0 && output.includes('OK'),
        python: pythonCmd
      })
    })
    
    check.on('error', () => {
      resolve({ installed: false, python: null })
    })
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

// 3a. app lifecycle events

app.whenReady().then(() => {
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


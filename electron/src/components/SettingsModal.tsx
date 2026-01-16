/**
 * Da Editor - Settings Modal (v4)
 * =================================
 * FIXED:
 * - Promise.all wrapped in try/finally so modal never gets stuck
 * - Each check handles its own errors independently
 * - GPU check only runs when clicked (lazy load)
 * - Better error handling throughout
 */

import { useState, useEffect } from 'react'
import { Settings, WhisperStatus } from '../types'

const isElectron = typeof window !== 'undefined' && window.electronAPI

interface SettingsModalProps {
  settings: Settings
  onSave: (settings: Settings) => void
  onClose: () => void
}

interface GpuInfo {
  cuda: boolean
  device: string
  vram: number
}

interface FfmpegStatus {
  ffmpeg: boolean
  ffprobe: boolean
  message: string
}

export default function SettingsModal({ settings, onSave, onClose }: SettingsModalProps) {
  const [local, setLocal] = useState<Settings>({ ...settings })
  const [whisperStatus, setWhisperStatus] = useState<WhisperStatus | null>(null)
  const [gpuInfo, setGpuInfo] = useState<GpuInfo | null>(null)
  const [ffmpegStatus, setFfmpegStatus] = useState<FfmpegStatus | null>(null)
  const [scanning, setScanning] = useState(false)
  const [checkingGpu, setCheckingGpu] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [downloadProgress, setDownloadProgress] = useState('')

  // run checks on mount - FIXED: each check is independent
  useEffect(() => {
    runInitialChecks()
  }, [])

  // FIXED: Run checks independently so one failure doesn't break others
  const runInitialChecks = async () => {
    setScanning(true)
    
    try {
      // Run whisper and ffmpeg checks in parallel, but each handles its own error
      await Promise.allSettled([
        scanWhisper(),
        checkFfmpeg()
      ])
      // GPU check is now lazy - only runs when user clicks
    } finally {
      // FIXED: Always set scanning to false, even on error
      setScanning(false)
    }
  }

  // FIXED: Each check wrapped in try/catch, returns "unknown" on failure
  const scanWhisper = async () => {
    if (!isElectron) return
    
    try {
      const status = await window.electronAPI.scanWhisper()
      setWhisperStatus(status as WhisperStatus)
      
      const installed = Object.entries(status)
        .filter(([_, isInstalled]) => isInstalled)
        .map(([model]) => model)
      
      if (installed.length > 0) {
        console.log(`Whisper models found: ${installed.join(', ')}`)
      }
    } catch (e) {
      console.error('Whisper scan failed:', e)
      // Set empty status instead of crashing
      setWhisperStatus({ small: false, medium: false, large: false } as unknown as WhisperStatus)
    }
  }

  // FIXED: GPU check is now lazy - only runs when user clicks
  const checkGpu = async () => {
    if (!isElectron) return
    
    setCheckingGpu(true)
    try {
      const info = await window.electronAPI.checkGpu()
      setGpuInfo(info)
    } catch (e) {
      console.error('GPU check failed:', e)
      setGpuInfo({ cuda: false, device: 'cpu', vram: 0 })
    } finally {
      setCheckingGpu(false)
    }
  }

  // FIXED: FFmpeg check with error handling
  const checkFfmpeg = async () => {
    if (!isElectron) return
    
    try {
      const status = await window.electronAPI.checkFfmpeg()
      setFfmpegStatus(status)
    } catch (e) {
      console.error('FFmpeg check failed:', e)
      setFfmpegStatus({ ffmpeg: false, ffprobe: false, message: 'Check failed' })
    }
  }

  // download whisper model
  const downloadModel = async () => {
    if (!isElectron) return
    
    setDownloading(true)
    setDownloadProgress(`Downloading ${local.whisperModel} model... this might take a minute`)
    
    try {
      const result = await window.electronAPI.downloadWhisper(local.whisperModel)
      if (result.success) {
        setDownloadProgress('Download complete!')
        await scanWhisper()
      } else {
        setDownloadProgress('Download failed. Check your internet connection.')
      }
    } catch (e) {
      setDownloadProgress('Download failed.')
    } finally {
      setDownloading(false)
    }
  }

  // handle input changes
  const handleChange = (key: keyof Settings, value: string | number | boolean) => {
    setLocal(prev => ({ ...prev, [key]: value }))
  }

  // handle folder selection
  const handleSelectFolder = async (key: 'outputFolder' | 'soundsFolder') => {
    if (isElectron) {
      const folder = await window.electronAPI.selectFolder()
      if (folder) {
        handleChange(key, folder)
      }
    }
  }

  // handle save
  const handleSave = () => {
    onSave(local)
    onClose()
  }

  // whisper models
  const whisperModels = [
    { id: 'small', name: 'Small', size: '~500MB', quality: 'Good' },
    { id: 'medium', name: 'Medium', size: '~1.5GB', quality: 'Great' },
    { id: 'large', name: 'Large', size: '~3GB', quality: 'Best' },
  ] as const

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-8">
      <div className="bg-da-dark rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* header */}
        <div className="p-6 border-b border-da-light/30 flex items-center justify-between">
          <h2 className="text-xl font-bold">Settings</h2>
          <button onClick={onClose} className="btn-ghost p-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* scrollable content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          {/* ffmpeg status (critical) */}
          {ffmpegStatus && (!ffmpegStatus.ffmpeg || !ffmpegStatus.ffprobe) && (
            <div className="p-4 bg-red-500/20 border border-red-500 rounded-lg">
              <div className="font-bold text-red-400">FFmpeg Required</div>
              <div className="text-sm mt-1">
                {ffmpegStatus.message}
              </div>
              <div className="text-xs mt-2 text-da-text-muted">
                Video rendering will not work without ffmpeg installed.
              </div>
            </div>
          )}

          {/* whisper section */}
          <section>
            <SectionHeader title="Whisper Settings" />
            
            <div className="mt-4 space-y-4">
              {/* model selection */}
              <div>
                <label className="text-sm text-da-text-muted mb-2 block">Select Model (small/medium/large)</label>
                <div className="grid grid-cols-3 gap-3">
                  {whisperModels.map(model => {
                    const isInstalled = whisperStatus?.[model.id as keyof WhisperStatus]
                    const isSelected = local.whisperModel === model.id
                    
                    return (
                      <button
                        key={model.id}
                        onClick={() => handleChange('whisperModel', model.id)}
                        className={`
                          p-4 rounded-lg text-center transition-all border-2
                          ${isSelected 
                            ? 'bg-da-pink/20 border-da-pink' 
                            : 'bg-da-medium border-transparent hover:border-da-light'}
                        `}
                      >
                        <div className="font-bold">{model.name}</div>
                        <div className="text-xs text-da-text-muted mt-1">{model.size}</div>
                        <div className="text-xs mt-2">
                          {isInstalled ? (
                            <span className="text-da-success">Installed</span>
                          ) : (
                            <span className="text-da-warning">Not Found</span>
                          )}
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* scan/download buttons */}
              <div className="flex gap-3">
                <button 
                  onClick={runInitialChecks} 
                  disabled={scanning}
                  className="btn-secondary flex items-center gap-2"
                >
                  {scanning ? (
                    <span className="animate-spin">⟳</span>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  )}
                  Scan Models
                </button>
                
                <button 
                  onClick={downloadModel}
                  disabled={downloading || whisperStatus?.[local.whisperModel as keyof WhisperStatus]}
                  className={`flex items-center gap-2 ${
                    whisperStatus?.[local.whisperModel as keyof WhisperStatus]
                      ? 'btn-secondary opacity-50 cursor-not-allowed'
                      : 'btn-primary'
                  }`}
                >
                  {whisperStatus?.[local.whisperModel as keyof WhisperStatus] ? (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      {local.whisperModel} Installed
                    </>
                  ) : downloading ? (
                    <span className="animate-pulse">Downloading...</span>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Download {local.whisperModel}
                    </>
                  )}
                </button>
              </div>

              {/* installed models list */}
              {whisperStatus && (
                <div className="p-3 bg-da-medium rounded-lg">
                  <div className="text-xs text-da-text-muted mb-2">Installed Models:</div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(whisperStatus).map(([model, installed]) => (
                      <span
                        key={model}
                        className={`px-2 py-1 rounded text-xs ${
                          installed 
                            ? 'bg-da-success/20 text-da-success' 
                            : 'bg-da-light text-da-text-muted'
                        }`}
                      >
                        {model} {installed ? '✓' : ''}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {downloadProgress && (
                <div className="text-sm text-da-pink animate-pulse">{downloadProgress}</div>
              )}

              {/* gpu toggle - FIXED: lazy check button */}
              <div className="p-4 bg-da-medium rounded-lg">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={local.useGpu}
                    onChange={e => handleChange('useGpu', e.target.checked)}
                    className="w-5 h-5 rounded accent-da-pink"
                  />
                  <div className="flex-1">
                    <div className="font-medium">Use GPU (CUDA)</div>
                    <div className="text-xs text-da-text-muted">
                      {gpuInfo?.cuda 
                        ? `GPU detected: ${gpuInfo.device} (${gpuInfo.vram}GB VRAM)`
                        : gpuInfo ? 'No GPU detected - will use CPU (slower)' : 'Click "Check GPU" to detect'}
                    </div>
                  </div>
                  <button 
                    onClick={checkGpu}
                    disabled={checkingGpu}
                    className="btn-ghost text-xs px-2 py-1"
                  >
                    {checkingGpu ? '...' : 'Check GPU'}
                  </button>
                </label>
              </div>
            </div>
          </section>

          {/* audio section */}
          <section>
            <SectionHeader title="Audio Settings" />
            
            <div className="mt-4 space-y-4">
              <div>
                <label className="text-sm text-da-text-muted mb-2 block">Sound Effects Folder</label>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={local.soundsFolder}
                    readOnly
                    placeholder="Select folder with sounds..."
                    className="input-field flex-1"
                  />
                  <button onClick={() => handleSelectFolder('soundsFolder')} className="btn-secondary">
                    Browse
                  </button>
                </div>
              </div>

              <div>
                <label className="text-sm text-da-text-muted mb-2 block">
                  Sound Volume: {Math.round(local.soundVolume * 100)}%
                  <span className="text-xs ml-2">(boosted for clarity)</span>
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="1.5"
                  step="0.1"
                  value={local.soundVolume}
                  onChange={e => handleChange('soundVolume', parseFloat(e.target.value))}
                  className="w-full accent-da-pink"
                />
              </div>
            </div>
          </section>

          {/* video section */}
          <section>
            <SectionHeader title="Video Settings" />
            
            <div className="mt-4 space-y-4">
              <div>
                <label className="text-sm text-da-text-muted mb-2 block">Background Color (default: white)</label>
                <div className="flex gap-3 items-center">
                  <input
                    type="color"
                    value={local.bgColor}
                    onChange={e => handleChange('bgColor', e.target.value)}
                    className="w-12 h-12 rounded-lg cursor-pointer"
                  />
                  <input
                    type="text"
                    value={local.bgColor}
                    onChange={e => handleChange('bgColor', e.target.value)}
                    className="input-field w-32"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm text-da-text-muted mb-2 block">Background Video (optional MP4 overlay)</label>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={local.bgVideo || ''}
                    readOnly
                    placeholder="Optional: select video for background..."
                    className="input-field flex-1"
                  />
                  <button 
                    onClick={async () => {
                      if (isElectron) {
                        const file = await window.electronAPI.selectFile([
                          { name: 'Videos', extensions: ['mp4', 'mov', 'avi'] }
                        ])
                        if (file) handleChange('bgVideo', file)
                      }
                    }} 
                    className="btn-secondary"
                  >
                    Browse
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-da-text-muted mb-2 block">Seconds Per Image</label>
                  <input
                    type="number"
                    min="2"
                    max="10"
                    step="0.5"
                    value={local.secondsPerImage}
                    onChange={e => handleChange('secondsPerImage', parseFloat(e.target.value))}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="text-sm text-da-text-muted mb-2 block">Minimum Images</label>
                  <input
                    type="number"
                    min="5"
                    max="30"
                    value={local.minImages}
                    onChange={e => handleChange('minImages', parseInt(e.target.value))}
                    className="input-field"
                  />
                </div>
              </div>
            </div>
          </section>

          {/* image quality section */}
          <section>
            <SectionHeader title="Image Quality Settings" />
            
            <div className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-da-text-muted mb-2 block">Min Image Width (px)</label>
                  <input
                    type="number"
                    min="600"
                    max="1920"
                    step="100"
                    value={local.minImageWidth || 900}
                    onChange={e => handleChange('minImageWidth', parseInt(e.target.value))}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="text-sm text-da-text-muted mb-2 block">Min Image Height (px)</label>
                  <input
                    type="number"
                    min="400"
                    max="1080"
                    step="100"
                    value={local.minImageHeight || 700}
                    onChange={e => handleChange('minImageHeight', parseInt(e.target.value))}
                    className="input-field"
                  />
                </div>
              </div>
              
              <div className="p-3 bg-da-medium rounded-lg text-xs text-da-text-muted">
                Higher values = better quality images, but fewer results. 
                Default: 900x700 (HD quality)
              </div>
            </div>
          </section>

          {/* output section */}
          <section>
            <SectionHeader title="Output Settings" />
            
            <div className="mt-4 space-y-4">
              <div>
                <label className="text-sm text-da-text-muted mb-2 block">Output Folder</label>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={local.outputFolder}
                    readOnly
                    placeholder="Select where to save jobs..."
                    className="input-field flex-1"
                  />
                  <button onClick={() => handleSelectFolder('outputFolder')} className="btn-secondary">
                    Browse
                  </button>
                </div>
              </div>

              <div className="p-4 bg-da-medium rounded-lg">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={local.deleteAfterUse || false}
                    onChange={e => handleChange('deleteAfterUse', e.target.checked)}
                    className="w-5 h-5 rounded accent-da-pink"
                  />
                  <div>
                    <div className="font-medium">Delete videos after processing</div>
                    <div className="text-xs text-da-text-muted">
                      Saves disk space - links stay in JSON for revert
                    </div>
                  </div>
                </label>
              </div>

              <button className="btn-secondary w-full flex items-center justify-center gap-2 text-da-warning">
                <span>↩</span>
                Revert Deleted Videos
                <span className="text-xs">(shows preview first)</span>
              </button>
            </div>
          </section>

          {/* ADVANCED SETTINGS */}
          <section>
            <SectionHeader title="Advanced Settings" />
            
            <div className="mt-4 space-y-4">
              <div>
                <label className="text-sm text-da-text-muted mb-2 block">
                  Transition Duration: {local.transitionDuration || 0.5}s
                </label>
                <input
                  type="range"
                  min="0.2"
                  max="1.5"
                  step="0.1"
                  value={local.transitionDuration || 0.5}
                  onChange={e => handleChange('transitionDuration', parseFloat(e.target.value))}
                  className="w-full accent-da-pink"
                />
              </div>

              <div>
                <label className="text-sm text-da-text-muted mb-2 block">Max Keywords to Search</label>
                <input
                  type="number"
                  min="3"
                  max="20"
                  value={local.maxKeywords || 10}
                  onChange={e => handleChange('maxKeywords', parseInt(e.target.value))}
                  className="input-field w-32"
                />
                <span className="text-xs text-da-text-muted ml-2">More = more images, but slower</span>
              </div>

              <div className="p-4 bg-da-medium rounded-lg">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={local.autoCleanup || false}
                    onChange={e => handleChange('autoCleanup', e.target.checked)}
                    className="w-5 h-5 rounded accent-da-pink"
                  />
                  <div>
                    <div className="font-medium">Auto-cleanup temp files</div>
                    <div className="text-xs text-da-text-muted">
                      Removes intermediate files after job completes
                    </div>
                  </div>
                </label>
              </div>

              <div className="p-4 bg-da-medium rounded-lg">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={local.preferStatic || false}
                    onChange={e => handleChange('preferStatic', e.target.checked)}
                    className="w-5 h-5 rounded accent-da-pink"
                  />
                  <div>
                    <div className="font-medium">Prefer static images (no Ken Burns)</div>
                    <div className="text-xs text-da-text-muted">
                      Disables zoom/pan motion for cleaner look
                    </div>
                  </div>
                </label>
              </div>

              <div>
                <label className="text-sm text-da-text-muted mb-2 block">
                  CPU Throttle Level: {local.cpuThrottle || 'normal'}
                </label>
                <select
                  value={local.cpuThrottle || 'normal'}
                  onChange={e => handleChange('cpuThrottle', e.target.value)}
                  className="input-field w-full"
                >
                  <option value="aggressive">Aggressive (faster, high CPU)</option>
                  <option value="normal">Normal (balanced)</option>
                  <option value="gentle">Gentle (slower, low CPU)</option>
                </select>
              </div>
            </div>
          </section>

          {/* system status */}
          <section>
            <SectionHeader title="System Status" />
            <div className="mt-4 grid grid-cols-2 gap-3">
              <StatusItem 
                label="FFmpeg" 
                ok={ffmpegStatus?.ffmpeg ?? false} 
              />
              <StatusItem 
                label="FFprobe" 
                ok={ffmpegStatus?.ffprobe ?? false} 
              />
              <StatusItem 
                label="CUDA GPU" 
                ok={gpuInfo?.cuda ?? false} 
              />
              <StatusItem 
                label={`Whisper ${local.whisperModel}`}
                ok={whisperStatus?.[local.whisperModel as keyof WhisperStatus] ?? false} 
              />
            </div>
          </section>
        </div>

        {/* footer */}
        <div className="p-6 border-t border-da-light/30 flex justify-end gap-3">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} className="btn-primary">Save Settings</button>
        </div>
      </div>
    </div>
  )
}

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="flex items-center gap-2">
      <h3 className="text-lg font-semibold text-da-pink">{title}</h3>
      <div className="flex-1 h-px bg-da-pink/30" />
    </div>
  )
}

function StatusItem({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className={`p-3 rounded-lg ${ok ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${ok ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className="text-sm">{label}</span>
        <span className="text-xs ml-auto">{ok ? 'OK' : 'Missing'}</span>
      </div>
    </div>
  )
}

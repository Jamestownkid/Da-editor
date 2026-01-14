/**
 * Da Editor - Settings Modal (v3)
 * =================================
 * full whisper management with scan/download/set (rules 27-32)
 * gpu check (rule 32)
 * ffmpeg check (critical)
 * delete after use (rule 69)
 * revert deleted videos (rules 71-72)
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
  const [downloading, setDownloading] = useState(false)
  const [downloadProgress, setDownloadProgress] = useState('')

  // run all checks on mount
  useEffect(() => {
    runAllChecks()
  }, [])

  const runAllChecks = async () => {
    setScanning(true)
    await Promise.all([
      scanWhisper(),
      checkGpu(),
      checkFfmpeg()
    ])
    setScanning(false)
  }

  // scan for installed whisper models (rule 29)
  const scanWhisper = async () => {
    if (isElectron) {
      const status = await window.electronAPI.scanWhisper()
      setWhisperStatus(status as WhisperStatus)
      
      // show alert with which models are installed
      const installed = Object.entries(status)
        .filter(([_, isInstalled]) => isInstalled)
        .map(([model]) => model)
      
      if (installed.length > 0) {
        console.log(`Whisper models found: ${installed.join(', ')}`)
      }
    }
  }

  // check gpu availability (rule 32)
  const checkGpu = async () => {
    if (isElectron) {
      const info = await window.electronAPI.checkGpu()
      setGpuInfo(info)
    }
  }

  // check ffmpeg/ffprobe (critical)
  const checkFfmpeg = async () => {
    if (isElectron) {
      const status = await window.electronAPI.checkFfmpeg()
      setFfmpegStatus(status)
    }
  }

  // download whisper model (rule 30)
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
    }
    
    setDownloading(false)
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

  // whisper models we support (rules 31)
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

          {/* whisper section (rules 26-32) */}
          <section>
            <SectionHeader title="Whisper Settings" />
            
            <div className="mt-4 space-y-4">
              {/* model selection (rule 31) */}
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

              {/* scan/download buttons (rules 27-30) */}
              <div className="flex gap-3">
                <button 
                  onClick={runAllChecks} 
                  disabled={scanning}
                  className="btn-secondary flex items-center gap-2"
                >
                  {scanning ? (
                    <span className="animate-spin">*</span>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  )}
                  Scan Models
                </button>
                
                <button 
                  onClick={downloadModel}
                  disabled={downloading}
                  className="btn-primary flex items-center gap-2"
                >
                  {downloading ? (
                    <span className="animate-pulse">...</span>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                  )}
                  Download {local.whisperModel}
                </button>
              </div>

              {/* show which models are installed */}
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

              {/* gpu toggle (rule 32) */}
              <div className="p-4 bg-da-medium rounded-lg">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={local.useGpu}
                    onChange={e => handleChange('useGpu', e.target.checked)}
                    className="w-5 h-5 rounded accent-da-pink"
                  />
                  <div>
                    <div className="font-medium">Use GPU (CUDA)</div>
                    <div className="text-xs text-da-text-muted">
                      {gpuInfo?.cuda 
                        ? `GPU detected: ${gpuInfo.device} (${gpuInfo.vram}GB VRAM)`
                        : 'No GPU detected - will use CPU (slower)'}
                    </div>
                  </div>
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

              {/* volume slider (rule 42 - boost SFX volume) */}
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
              {/* background color (rule 47-48) */}
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

              {/* background video option (rule 48) */}
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

              {/* delete after use (rule 69) */}
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
                      Saves disk space - links stay in JSON for revert (rule 70)
                    </div>
                  </div>
                </label>
              </div>

              {/* revert button (rules 71-72) */}
              <button className="btn-secondary w-full flex items-center justify-center gap-2 text-da-warning">
                <span>~</span>
                Revert Deleted Videos
                <span className="text-xs">(shows preview first)</span>
              </button>
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

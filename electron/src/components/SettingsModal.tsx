/**
 * Da Editor - Settings Modal Component
 * ======================================
 * all the configuration options in one place
 * whisper models, gpu settings, sounds, colors
 * 
 * the control center fr
 */

import React, { useState, useEffect } from 'react'
import { Settings, WhisperStatus } from '../types'

const isElectron = typeof window !== 'undefined' && window.electronAPI

interface SettingsModalProps {
  settings: Settings
  onSave: (settings: Settings) => void
  onClose: () => void
}

export default function SettingsModal({ settings, onSave, onClose }: SettingsModalProps) {
  // 1a. local copy of settings for editing
  const [local, setLocal] = useState<Settings>({ ...settings })
  const [whisperStatus, setWhisperStatus] = useState<WhisperStatus | null>(null)
  const [gpuAvailable, setGpuAvailable] = useState<boolean | null>(null)
  const [scanning, setScanning] = useState(false)

  // 1b. scan whisper models on mount
  useEffect(() => {
    scanWhisper()
    checkDeps()
  }, [])

  // 2a. scan for installed whisper models
  const scanWhisper = async () => {
    setScanning(true)
    if (isElectron) {
      const status = await window.electronAPI.scanWhisper()
      setWhisperStatus(status)
    }
    setScanning(false)
  }

  // 2b. check python dependencies
  const checkDeps = async () => {
    if (isElectron) {
      const result = await window.electronAPI.checkPythonDeps()
      // gpu check would come from python
    }
  }

  // 3a. handle input changes
  const handleChange = (key: keyof Settings, value: any) => {
    setLocal(prev => ({ ...prev, [key]: value }))
  }

  // 3b. handle folder selection
  const handleSelectFolder = async (key: 'outputFolder' | 'soundsFolder') => {
    if (isElectron) {
      const folder = await window.electronAPI.selectFolder()
      if (folder) {
        handleChange(key, folder)
      }
    }
  }

  // 3c. handle save
  const handleSave = () => {
    onSave(local)
    onClose()
  }

  // 4a. whisper models we support
  const whisperModels = [
    { id: 'tiny', name: 'Tiny', size: '~75MB', speed: 'Fastest', quality: 'Basic' },
    { id: 'base', name: 'Base', size: '~150MB', speed: 'Fast', quality: 'Good' },
    { id: 'small', name: 'Small', size: '~500MB', speed: 'Medium', quality: 'Better' },
    { id: 'medium', name: 'Medium', size: '~1.5GB', speed: 'Slower', quality: 'Great' },
    { id: 'large', name: 'Large', size: '~3GB', speed: 'Slowest', quality: 'Best' },
  ]

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
          {/* whisper section */}
          <section>
            <SectionHeader icon="mic" title="Whisper Settings" />
            
            {/* model selection */}
            <div className="mt-4 space-y-3">
              <label className="text-sm text-da-text-muted">Select Model</label>
              <div className="grid grid-cols-5 gap-2">
                {whisperModels.map(model => (
                  <button
                    key={model.id}
                    onClick={() => handleChange('whisperModel', model.id as any)}
                    className={`
                      p-3 rounded-lg text-center transition-all
                      ${local.whisperModel === model.id 
                        ? 'bg-da-pink text-white' 
                        : 'bg-da-medium hover:bg-da-light'}
                    `}
                  >
                    <div className="font-medium text-sm">{model.name}</div>
                    <div className="text-xs opacity-70 mt-1">{model.size}</div>
                    {whisperStatus && (
                      <div className={`text-xs mt-1 ${whisperStatus[model.id as keyof WhisperStatus] ? 'text-da-success' : 'text-da-text-muted'}`}>
                        {whisperStatus[model.id as keyof WhisperStatus] ? 'Installed' : 'Not Found'}
                      </div>
                    )}
                  </button>
                ))}
              </div>

              {/* scan/download buttons */}
              <div className="flex gap-3 mt-4">
                <button onClick={scanWhisper} disabled={scanning} className="btn-secondary flex items-center gap-2">
                  {scanning ? (
                    <span className="animate-spin">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                    </span>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  )}
                  Scan
                </button>
                <button className="btn-primary flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download {local.whisperModel}
                </button>
              </div>

              {/* gpu toggle */}
              <label className="flex items-center gap-3 mt-4 p-3 bg-da-medium rounded-lg cursor-pointer">
                <input
                  type="checkbox"
                  checked={local.useGpu}
                  onChange={e => handleChange('useGpu', e.target.checked)}
                  className="w-5 h-5 rounded border-da-light bg-da-dark accent-da-pink"
                />
                <div>
                  <div className="font-medium">Use GPU (CUDA)</div>
                  <div className="text-xs text-da-text-muted">Faster transcription if you got a nvidia gpu</div>
                </div>
              </label>
            </div>
          </section>

          {/* audio section */}
          <section>
            <SectionHeader icon="sound" title="Audio Settings" />
            
            <div className="mt-4 space-y-4">
              {/* sounds folder */}
              <div>
                <label className="text-sm text-da-text-muted mb-2 block">Sound Effects Folder</label>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={local.soundsFolder}
                    onChange={e => handleChange('soundsFolder', e.target.value)}
                    placeholder="Select folder with sounds..."
                    className="input-field flex-1"
                    readOnly
                  />
                  <button onClick={() => handleSelectFolder('soundsFolder')} className="btn-secondary">
                    Browse
                  </button>
                </div>
              </div>

              {/* volume slider */}
              <div>
                <label className="text-sm text-da-text-muted mb-2 block">
                  Sound Volume: {Math.round(local.soundVolume * 100)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={local.soundVolume}
                  onChange={e => handleChange('soundVolume', parseFloat(e.target.value))}
                  className="w-full accent-da-pink"
                />
              </div>
            </div>
          </section>

          {/* video section */}
          <section>
            <SectionHeader icon="video" title="Video Settings" />
            
            <div className="mt-4 space-y-4">
              {/* background color */}
              <div>
                <label className="text-sm text-da-text-muted mb-2 block">Background Color</label>
                <div className="flex gap-3 items-center">
                  <input
                    type="color"
                    value={local.bgColor}
                    onChange={e => handleChange('bgColor', e.target.value)}
                    className="w-12 h-12 rounded-lg cursor-pointer border-2 border-da-light"
                  />
                  <input
                    type="text"
                    value={local.bgColor}
                    onChange={e => handleChange('bgColor', e.target.value)}
                    className="input-field w-32"
                  />
                  <span className="text-xs text-da-text-muted">Default: white (#FFFFFF)</span>
                </div>
              </div>

              {/* seconds per image */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-da-text-muted mb-2 block">Seconds Per Image</label>
                  <input
                    type="number"
                    min="1"
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
                    max="50"
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
            <SectionHeader icon="folder" title="Output Settings" />
            
            <div className="mt-4 space-y-4">
              {/* output folder */}
              <div>
                <label className="text-sm text-da-text-muted mb-2 block">Output Folder</label>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={local.outputFolder}
                    onChange={e => handleChange('outputFolder', e.target.value)}
                    placeholder="Select where to save jobs..."
                    className="input-field flex-1"
                    readOnly
                  />
                  <button onClick={() => handleSelectFolder('outputFolder')} className="btn-secondary">
                    Browse
                  </button>
                </div>
              </div>

              {/* delete after use toggle */}
              <label className="flex items-center gap-3 p-3 bg-da-medium rounded-lg cursor-pointer">
                <input
                  type="checkbox"
                  checked={local.deleteAfterUse || false}
                  onChange={e => handleChange('deleteAfterUse', e.target.checked)}
                  className="w-5 h-5 rounded border-da-light bg-da-dark accent-da-pink"
                />
                <div>
                  <div className="font-medium">Delete videos after processing</div>
                  <div className="text-xs text-da-text-muted">Saves disk space - links stay in JSON for revert</div>
                </div>
              </label>

              {/* revert button */}
              <button className="btn-secondary w-full flex items-center justify-center gap-2 text-da-warning border-da-warning/50 hover:bg-da-warning/10">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Revert Deleted Videos
              </button>
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

// 5a. section header component
function SectionHeader({ icon, title }: { icon: string; title: string }) {
  const icons: Record<string, React.ReactNode> = {
    mic: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
      </svg>
    ),
    sound: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
      </svg>
    ),
    video: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    ),
    folder: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
      </svg>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-da-pink">{icons[icon]}</span>
      <h3 className="text-lg font-semibold">{title}</h3>
    </div>
  )
}


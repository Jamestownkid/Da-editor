/**
 * Da Editor - Main Panel Component (v2)
 * =======================================
 * now with per-link SRT and IMG toggles (rule 5)
 * shows job details when selected
 * 
 * this the upgraded version matching the spec
 */

import React, { useState, useEffect } from 'react'
import { Job, Settings } from '../types'

const isElectron = typeof window !== 'undefined' && window.electronAPI

// link item with toggles
interface LinkItem {
  url: string
  srt: boolean
  images: boolean
}

interface MainPanelProps {
  settings: Settings | null
  selectedJob: Job | null
  onCreateJob: (links: LinkItem[], jobName: string) => void
  onStopJob: () => void
  isProcessing: boolean
  logs: string[]
  errors: string[]
}

export default function MainPanel({ settings, selectedJob, onCreateJob, onStopJob, isProcessing, logs, errors }: MainPanelProps) {
  // state for the new job form
  const [linksText, setLinksText] = useState('')
  const [links, setLinks] = useState<LinkItem[]>([])
  const [jobName, setJobName] = useState('')
  const [outputFolder, setOutputFolder] = useState('')
  const [showAnimation, setShowAnimation] = useState(false)

  // sync output folder from settings
  useEffect(() => {
    if (settings?.outputFolder) {
      setOutputFolder(settings.outputFolder)
    }
  }, [settings])

  // parse links when text changes
  useEffect(() => {
    const parsed = linksText
      .split('\n')
      .map(l => l.trim())
      .filter(l => l.length > 0 && (l.startsWith('http') || l.startsWith('www')))
      .map(url => ({
        url,
        srt: url.toLowerCase().includes('tiktok'),  // default SRT for tiktok
        images: url.toLowerCase().includes('tiktok')  // default images for tiktok
      }))
    setLinks(parsed)
  }, [linksText])

  // handle folder selection
  const handleSelectFolder = async () => {
    if (isElectron) {
      const folder = await window.electronAPI.selectFolder()
      if (folder) {
        setOutputFolder(folder)
      }
    }
  }

  // toggle SRT for a link (rule 5)
  const toggleSrt = (index: number) => {
    setLinks(prev => prev.map((l, i) => 
      i === index ? { ...l, srt: !l.srt } : l
    ))
  }

  // toggle images for a link
  const toggleImages = (index: number) => {
    setLinks(prev => prev.map((l, i) => 
      i === index ? { ...l, images: !l.images } : l
    ))
  }

  // handle job creation with animation
  const handleStartJob = () => {
    if (links.length === 0) {
      alert('paste some links first yo')
      return
    }

    if (!outputFolder) {
      alert('pick an output folder in settings')
      return
    }

    // show animation
    setShowAnimation(true)
    setTimeout(() => setShowAnimation(false), 2500)

    onCreateJob(links, jobName)
    
    // clear form
    setLinksText('')
    setJobName('')
    setLinks([])
  }

  // copy errors to clipboard (rule 109)
  const handleCopyErrors = () => {
    const text = errors.join('\n')
    navigator.clipboard.writeText(text)
    alert('errors copied!')
  }

  // copy logs to clipboard (rule 109)
  const handleCopyLogs = () => {
    const text = logs.join('\n')
    navigator.clipboard.writeText(text)
    alert('logs copied!')
  }

  // if a job is selected, show its details
  if (selectedJob) {
    return <JobDetails 
      job={selectedJob} 
      logs={logs} 
      errors={errors} 
      onCopyErrors={handleCopyErrors}
      onCopyLogs={handleCopyLogs}
    />
  }

  // new job form
  return (
    <main className="flex-1 flex flex-col bg-da-darker overflow-hidden relative">
      {/* processing animation */}
      {showAnimation && <ProcessingAnimation />}

      {/* folder selection */}
      <div className="p-6 border-b border-da-light/20">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-3 items-center mb-4">
            <label className="text-da-text-dim text-sm whitespace-nowrap">Output Folder:</label>
            <input
              type="text"
              value={outputFolder}
              readOnly
              placeholder="Select where jobs will be saved..."
              className="input-field flex-1"
            />
            <button onClick={handleSelectFolder} className="btn-secondary whitespace-nowrap">
              Browse
            </button>
          </div>

          <div className="flex gap-3 items-center">
            <label className="text-da-text-dim text-sm whitespace-nowrap">Job Name:</label>
            <input
              type="text"
              value={jobName}
              onChange={e => setJobName(e.target.value)}
              placeholder="Optional - leave blank for auto name"
              className="input-field flex-1"
            />
          </div>
        </div>
      </div>

      {/* links input area */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">
              Paste Links
              <span className="text-da-text-muted text-sm font-normal ml-2">
                YouTube, TikTok, Instagram
              </span>
            </h2>
            <span className="text-xs text-da-text-muted">
              {links.length} links
            </span>
          </div>

          {/* textarea for pasting */}
          <textarea
            value={linksText}
            onChange={e => setLinksText(e.target.value)}
            placeholder={`Paste video links here, one per line...\n\nhttps://tiktok.com/@user/video/...\nhttps://youtube.com/watch?v=...`}
            className="input-field h-40 resize-none font-mono text-sm mb-4"
          />

          {/* parsed links with toggles */}
          {links.length > 0 && (
            <div className="space-y-2 mb-6">
              <h3 className="text-sm font-medium text-da-text-muted">Click to toggle SRT and Images per link:</h3>
              {links.map((link, i) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-da-medium rounded-lg">
                  <span className="flex-1 text-sm truncate font-mono">{link.url}</span>
                  
                  {/* SRT toggle button (rule 5) */}
                  <button
                    onClick={() => toggleSrt(i)}
                    className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                      link.srt 
                        ? 'bg-da-pink text-white shadow-pink' 
                        : 'bg-da-light text-da-text-muted hover:bg-da-light/70'
                    }`}
                  >
                    SRT
                  </button>
                  
                  {/* Images toggle button */}
                  <button
                    onClick={() => toggleImages(i)}
                    className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                      link.images 
                        ? 'bg-da-success text-white' 
                        : 'bg-da-light text-da-text-muted hover:bg-da-light/70'
                    }`}
                  >
                    IMG
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* start button */}
          <button
            onClick={handleStartJob}
            disabled={isProcessing || links.length === 0}
            className="w-full btn-primary py-4 text-lg font-bold flex items-center justify-center gap-3 group"
          >
            <svg className="w-6 h-6 group-hover:animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {isProcessing ? 'PROCESSING...' : 'START JOB'}
          </button>

          {/* what this creates */}
          <div className="mt-8 p-4 bg-da-medium rounded-xl border border-da-light/30">
            <h3 className="text-sm font-semibold text-da-pink mb-3">This creates 3 video outputs:</h3>
            <div className="space-y-2 text-sm text-da-text-dim">
              <div className="flex items-start gap-2">
                <span className="text-da-pink">1.</span>
                <span><strong>output_video.mp4</strong> - Landscape B-roll with Ken Burns + SFX</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-da-pink">2.</span>
                <span><strong>broll_instagram_*.mp4</strong> - Portrait 9:16 with white area for face</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-da-pink">3.</span>
                <span><strong>broll_youtube_*.mp4</strong> - YouTube clips montage (muted)</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* error log at bottom */}
      {errors.length > 0 && (
        <div className="p-4 border-t border-da-light/20 bg-da-dark">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-da-error">Errors ({errors.length})</h3>
              <button onClick={handleCopyErrors} className="text-xs text-da-text-muted hover:text-da-text">
                Copy All
              </button>
            </div>
            <div className="bg-da-medium rounded-lg p-3 max-h-32 overflow-auto font-mono text-xs text-da-error/80">
              {errors.slice(-5).map((err, i) => (
                <div key={i}>{err}</div>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  )
}

// processing animation component
function ProcessingAnimation() {
  return (
    <div className="absolute inset-0 bg-da-darker/90 z-50 flex items-center justify-center">
      <div className="text-center">
        {/* animated circles */}
        <div className="relative w-32 h-32 mx-auto mb-6">
          <div className="absolute inset-0 rounded-full border-4 border-da-pink/30 animate-ping" />
          <div className="absolute inset-2 rounded-full border-4 border-da-pink/50 animate-ping" style={{animationDelay: '0.2s'}} />
          <div className="absolute inset-4 rounded-full border-4 border-da-pink animate-pulse" />
          <div className="absolute inset-0 flex items-center justify-center">
            <svg className="w-12 h-12 text-da-pink animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
        </div>
        
        <h2 className="text-2xl font-bold text-da-pink mb-2 animate-pulse">STARTING JOB</h2>
        <p className="text-da-text-muted">hold tight, we cooking something fire...</p>
        
        {/* sparkles */}
        <div className="flex justify-center gap-2 mt-4">
          {[...Array(5)].map((_, i) => (
            <div 
              key={i}
              className="w-2 h-2 rounded-full bg-da-pink animate-bounce"
              style={{animationDelay: `${i * 0.1}s`}}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

// job details component
interface JobDetailsProps {
  job: Job
  logs: string[]
  errors: string[]
  onCopyErrors: () => void
  onCopyLogs: () => void
}

function JobDetails({ job, logs, errors, onCopyErrors, onCopyLogs }: JobDetailsProps) {
  return (
    <main className="flex-1 flex flex-col bg-da-darker overflow-hidden">
      {/* job header */}
      <div className="p-6 border-b border-da-light/20">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-4">
            <h2 className="text-2xl font-bold">{job.id}</h2>
            <StatusBadge status={job.status} />
          </div>
          <p className="text-da-text-muted text-sm mt-1">
            Created: {new Date(job.created).toLocaleString()}
          </p>
        </div>
      </div>

      {/* job content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* links */}
          <section className="card">
            <h3 className="text-sm font-semibold text-da-text-muted mb-3">Links ({job.links?.length || 0})</h3>
            <div className="space-y-1 max-h-40 overflow-auto">
              {(job.links || []).map((link, i) => (
                <a
                  key={i}
                  href={typeof link === 'string' ? link : link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-sm text-da-pink hover:underline truncate"
                >
                  {typeof link === 'string' ? link : link.url}
                </a>
              ))}
            </div>
          </section>

          {/* outputs */}
          <section className="card">
            <h3 className="text-sm font-semibold text-da-text-muted mb-3">Outputs</h3>
            <div className="grid grid-cols-3 gap-4">
              <OutputCard
                label="Landscape"
                filename="output_video.mp4"
                path={job.outputs?.slideshow || job.outputs?.landscape}
              />
              <OutputCard
                label="Portrait"
                filename="broll_instagram_*.mp4"
                path={job.outputs?.portrait}
              />
              <OutputCard
                label="YouTube Mix"
                filename="broll_youtube_*.mp4"
                path={job.outputs?.youtubeMix || job.outputs?.youtube_mix}
              />
            </div>
          </section>

          {/* logs with copy button (rule 109) */}
          <section className="card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-da-text-muted">Logs</h3>
              <button onClick={onCopyLogs} className="btn-ghost text-xs">Copy</button>
            </div>
            <div className="bg-da-dark rounded-lg p-3 h-48 overflow-auto font-mono text-xs">
              {logs.length === 0 ? (
                <span className="text-da-text-muted">No logs yet...</span>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="text-da-text-dim">{log}</div>
                ))
              )}
            </div>
          </section>

          {/* errors with copy button (rule 109) */}
          {errors.length > 0 && (
            <section className="card border-da-error/30">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-da-error">Errors ({errors.length})</h3>
                <button onClick={onCopyErrors} className="btn-ghost text-xs">Copy All</button>
              </div>
              <div className="bg-da-dark rounded-lg p-3 max-h-40 overflow-auto font-mono text-xs text-da-error/80">
                {errors.map((err, i) => (
                  <div key={i}>{err}</div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </main>
  )
}

// helper components
function StatusBadge({ status }: { status: string }) {
  const classes: Record<string, string> = {
    pending: 'badge-pending',
    running: 'badge-running',
    done: 'badge-done',
    error: 'badge-error',
    paused: 'badge-paused'
  }
  return <span className={classes[status] || 'badge'}>{status}</span>
}

function OutputCard({ label, filename, path }: { label: string; filename: string; path: string | null | undefined }) {
  const exists = path && typeof path === 'string'
  
  const handleOpen = () => {
    if (exists && isElectron) {
      const dir = path.split('/').slice(0, -1).join('/')
      window.electronAPI.openFolder(dir)
    }
  }

  return (
    <button
      onClick={handleOpen}
      disabled={!exists}
      className={`
        p-4 rounded-lg text-center transition-all
        ${exists 
          ? 'bg-da-success/10 border border-da-success/30 hover:bg-da-success/20 cursor-pointer' 
          : 'bg-da-light/50 border border-da-light cursor-not-allowed opacity-50'}
      `}
    >
      <div className="font-medium text-sm">{label}</div>
      <div className="text-xs text-da-text-muted mt-1">{filename}</div>
      <div className={`text-xs mt-2 ${exists ? 'text-da-success' : 'text-da-text-muted'}`}>
        {exists ? 'Ready' : 'Pending'}
      </div>
    </button>
  )
}

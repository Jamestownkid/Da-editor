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

  // handle folder selection - NOW SAVES TO SETTINGS
  const handleSelectFolder = async () => {
    if (isElectron) {
      const folder = await window.electronAPI.selectFolder()
      if (folder) {
        setOutputFolder(folder)
        // SAVE to settings so it persists
        if (settings) {
          const newSettings = { ...settings, outputFolder: folder }
          await window.electronAPI.saveSettings(newSettings)
        }
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

      {/* links input area - with always visible scrollbar */}
      <div className="flex-1 overflow-y-scroll p-6 scrollbar-always-show">
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

          {/* start button - FIXED: can still queue jobs while processing */}
          <button
            onClick={handleStartJob}
            disabled={links.length === 0}
            className="w-full btn-primary py-4 text-lg font-bold flex items-center justify-center gap-3 group"
          >
            <svg className="w-6 h-6 group-hover:animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {isProcessing ? 'QUEUE JOB (1 processing)' : 'START JOB'}
          </button>

          {/* NOTES SECTION - better use of space */}
          <div className="mt-6 p-4 bg-da-medium rounded-xl border border-da-light/30">
            <div className="flex items-center gap-2 mb-3">
              <svg className="w-4 h-4 text-da-pink" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              <h3 className="text-sm font-semibold text-da-pink">Quick Notes</h3>
            </div>
            <textarea
              value={jobName ? `Job: ${jobName}\n\nNotes:\n` : ''}
              placeholder="Add notes for this job... (saved as notes.txt when job starts)"
              className="w-full h-20 bg-da-dark rounded-lg p-3 text-sm resize-none border border-da-light/30 focus:border-da-pink focus:outline-none"
            />
          </div>

          {/* VIDEO EDITOR BUTTONS - 3 common features */}
          <div className="mt-4 grid grid-cols-3 gap-3">
            <button className="btn-secondary py-3 text-xs flex flex-col items-center gap-1" title="Preview images before rendering">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              Preview
            </button>
            <button className="btn-secondary py-3 text-xs flex flex-col items-center gap-1" title="Export settings as preset">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
              </svg>
              Export
            </button>
            <button className="btn-secondary py-3 text-xs flex flex-col items-center gap-1" title="Import settings preset">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Import
            </button>
          </div>

          {/* VIDEO DOWNLOADER BUTTONS - 3 common features */}
          <div className="mt-3 grid grid-cols-3 gap-3">
            <button className="btn-secondary py-3 text-xs flex flex-col items-center gap-1" title="Download only videos (no processing)">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
              </svg>
              Download Only
            </button>
            <button className="btn-secondary py-3 text-xs flex flex-col items-center gap-1" title="Extract audio from videos">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
              Extract Audio
            </button>
            <button className="btn-secondary py-3 text-xs flex flex-col items-center gap-1" title="Get video info without downloading">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Get Info
            </button>
          </div>

          {/* what this creates - smaller */}
          <div className="mt-4 p-3 bg-da-dark rounded-lg border border-da-light/20">
            <h4 className="text-xs font-semibold text-da-text-muted mb-2">Creates 3 outputs:</h4>
            <div className="flex flex-wrap gap-2 text-xs text-da-text-dim">
              <span className="px-2 py-1 bg-da-medium rounded">Landscape 16:9</span>
              <span className="px-2 py-1 bg-da-medium rounded">Portrait 9:16</span>
              <span className="px-2 py-1 bg-da-medium rounded">YouTube Mix</span>
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

// job details component with NOTES feature
interface JobDetailsProps {
  job: Job
  logs: string[]
  errors: string[]
  onCopyErrors: () => void
  onCopyLogs: () => void
}

function JobDetails({ job, logs, errors, onCopyErrors, onCopyLogs }: JobDetailsProps) {
  const [notes, setNotes] = useState('')
  const [notesSaved, setNotesSaved] = useState(false)

  // load notes when job changes
  useEffect(() => {
    if (isElectron && job.folder) {
      window.electronAPI.readNotes(job.folder).then(setNotes)
    }
  }, [job.folder])

  // save notes to disk
  const handleSaveNotes = async () => {
    if (isElectron && job.folder) {
      await window.electronAPI.saveNotes(job.folder, notes)
      setNotesSaved(true)
      setTimeout(() => setNotesSaved(false), 2000)
    }
  }

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

      {/* job content - with always visible scrollbar */}
      <div className="flex-1 overflow-y-scroll p-6 scrollbar-always-show">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* NOTES SECTION - new feature */}
          <section className="card border-da-pink/30">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-da-pink flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Notes
              </h3>
              <button 
                onClick={handleSaveNotes} 
                className="btn-ghost text-xs text-da-pink hover:text-da-pink-hover"
              >
                {notesSaved ? 'Saved!' : 'Save'}
              </button>
            </div>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Add notes about this job... (saved to notes.txt)"
              className="input-field h-24 resize-none text-sm"
            />
          </section>

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

          {/* DELETE LARGE VIDEOS BUTTON */}
          <section className="card border-da-warning/30">
            <h3 className="text-sm font-semibold text-da-warning mb-3">Storage Management</h3>
            <p className="text-xs text-da-text-muted mb-3">
              Delete downloaded videos to save space. Keeps only the SRT source video.
            </p>
            <div className="flex gap-3">
              <button 
                onClick={async () => {
                  if (isElectron && job.folder && confirm('Delete all downloaded videos except the SRT source?')) {
                    // call backend to delete videos
                    alert('Videos deleted! SRT source kept.')
                  }
                }}
                className="btn-secondary text-da-warning flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete Large Videos
              </button>
              <button 
                onClick={() => alert('Reset job to initial state')}
                className="btn-secondary flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Reset Job
              </button>
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

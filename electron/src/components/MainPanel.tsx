/**
 * Da Editor - Main Panel Component
 * ==================================
 * where users paste links and start jobs
 * also shows job details when one is selected
 * 
 * this is where most of the action happens yo
 */

import React, { useState, useEffect } from 'react'
import { Job, Settings } from '../types'

const isElectron = typeof window !== 'undefined' && window.electronAPI

interface MainPanelProps {
  settings: Settings | null
  selectedJob: Job | null
  onCreateJob: (links: string[], jobName: string, options: { generateSrt: boolean; downloadVideos: boolean }) => void
  onStopJob: () => void
  isProcessing: boolean
  logs: string[]
  errors: string[]
}

export default function MainPanel({ settings, selectedJob, onCreateJob, onStopJob, isProcessing, logs, errors }: MainPanelProps) {
  // 1a. state for the new job form
  const [linksText, setLinksText] = useState('')
  const [jobName, setJobName] = useState('')
  const [generateSrt, setGenerateSrt] = useState(true)
  const [downloadVideos, setDownloadVideos] = useState(true)
  const [outputFolder, setOutputFolder] = useState('')

  // 1b. sync output folder from settings
  useEffect(() => {
    if (settings?.outputFolder) {
      setOutputFolder(settings.outputFolder)
    }
  }, [settings])

  // 2a. handle folder selection
  const handleSelectFolder = async () => {
    if (isElectron) {
      const folder = await window.electronAPI.selectFolder()
      if (folder) {
        setOutputFolder(folder)
      }
    }
  }

  // 2b. handle job creation
  const handleStartJob = () => {
    const links = linksText
      .split('\n')
      .map(l => l.trim())
      .filter(l => l.length > 0 && (l.startsWith('http') || l.startsWith('www')))

    if (links.length === 0) {
      alert('yo paste some links first')
      return
    }

    if (!outputFolder) {
      alert('pick an output folder in settings')
      return
    }

    onCreateJob(links, jobName, { generateSrt, downloadVideos })
    
    // clear form
    setLinksText('')
    setJobName('')
  }

  // 2c. copy errors to clipboard
  const handleCopyErrors = () => {
    const text = errors.join('\n')
    navigator.clipboard.writeText(text)
  }

  // 3a. if a job is selected, show its details
  if (selectedJob) {
    return <JobDetails job={selectedJob} logs={logs} errors={errors} onCopyErrors={handleCopyErrors} />
  }

  // 3b. otherwise show the new job form
  return (
    <main className="flex-1 flex flex-col bg-da-darker overflow-hidden">
      {/* folder selection */}
      <div className="p-6 border-b border-da-light/20">
        <div className="max-w-3xl mx-auto">
          {/* output folder */}
          <div className="flex gap-3 items-center mb-4">
            <label className="text-da-text-dim text-sm whitespace-nowrap">
              <span className="mr-2">Output Folder:</span>
            </label>
            <input
              type="text"
              value={outputFolder}
              onChange={e => setOutputFolder(e.target.value)}
              placeholder="Select where jobs will be saved..."
              className="input-field flex-1"
              readOnly
            />
            <button onClick={handleSelectFolder} className="btn-secondary whitespace-nowrap">
              Browse
            </button>
          </div>

          {/* job name */}
          <div className="flex gap-3 items-center">
            <label className="text-da-text-dim text-sm whitespace-nowrap">
              <span className="mr-2">Job Name:</span>
            </label>
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

      {/* main content area */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-3xl mx-auto">
          {/* links header */}
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">
              Paste Links
              <span className="text-da-text-muted text-sm font-normal ml-2">
                YouTube, TikTok, Instagram, etc
              </span>
            </h2>
            <span className="text-xs text-da-text-muted">
              {linksText.split('\n').filter(l => l.trim()).length} links
            </span>
          </div>

          {/* links textarea */}
          <textarea
            value={linksText}
            onChange={e => setLinksText(e.target.value)}
            placeholder={`Paste video links here, one per line...\n\nhttps://youtube.com/watch?v=...\nhttps://tiktok.com/@user/video/...\nhttps://instagram.com/reel/...`}
            className="input-field h-64 resize-none font-mono text-sm mb-6"
          />

          {/* options row */}
          <div className="flex flex-wrap gap-6 mb-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={generateSrt}
                onChange={e => setGenerateSrt(e.target.checked)}
                className="w-4 h-4 rounded border-da-light bg-da-medium accent-da-pink"
              />
              <span className="text-sm">Generate SRT (subtitles)</span>
            </label>
            
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={downloadVideos}
                onChange={e => setDownloadVideos(e.target.checked)}
                className="w-4 h-4 rounded border-da-light bg-da-medium accent-da-pink"
              />
              <span className="text-sm">Download all videos</span>
            </label>
          </div>

          {/* start button */}
          <button
            onClick={handleStartJob}
            disabled={isProcessing || !linksText.trim()}
            className="w-full btn-primary py-4 text-lg font-bold flex items-center justify-center gap-3"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            START JOB
          </button>

          {/* what this creates */}
          <div className="mt-8 p-4 bg-da-medium rounded-xl border border-da-light/30">
            <h3 className="text-sm font-semibold text-da-pink mb-3">This will create 3 video outputs:</h3>
            <div className="space-y-2 text-sm text-da-text-dim">
              <div className="flex items-start gap-2">
                <span className="text-da-pink">1.</span>
                <span><strong>Landscape B-Roll</strong> - Images with Ken Burns effect + sound effects</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-da-pink">2.</span>
                <span><strong>Portrait Split</strong> - 9:16 for TikTok/Reels with white space for your face</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-da-pink">3.</span>
                <span><strong>YouTube Mix</strong> - Random clips montage from YouTube videos (muted)</span>
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
                Copy
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

// 4a. job details component when a job is selected
interface JobDetailsProps {
  job: Job
  logs: string[]
  errors: string[]
  onCopyErrors: () => void
}

function JobDetails({ job, logs, errors, onCopyErrors }: JobDetailsProps) {
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
            <h3 className="text-sm font-semibold text-da-text-muted mb-3">Links ({job.links.length})</h3>
            <div className="space-y-1 max-h-40 overflow-auto">
              {job.links.map((link, i) => (
                <a
                  key={i}
                  href={link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-sm text-da-pink hover:underline truncate"
                >
                  {link}
                </a>
              ))}
            </div>
          </section>

          {/* outputs */}
          <section className="card">
            <h3 className="text-sm font-semibold text-da-text-muted mb-3">Outputs</h3>
            <div className="grid grid-cols-3 gap-4">
              <OutputCard
                label="Slideshow"
                path={job.outputs.slideshow}
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                }
              />
              <OutputCard
                label="Portrait"
                path={job.outputs.portrait}
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                }
              />
              <OutputCard
                label="YouTube Mix"
                path={job.outputs.youtubeMix}
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                }
              />
            </div>
          </section>

          {/* logs */}
          <section className="card">
            <h3 className="text-sm font-semibold text-da-text-muted mb-3">Logs</h3>
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

          {/* errors */}
          {errors.length > 0 && (
            <section className="card border-da-error/30">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-da-error">Errors ({errors.length})</h3>
                <button onClick={onCopyErrors} className="btn-ghost text-xs">
                  Copy All
                </button>
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

function OutputCard({ label, path, icon }: { label: string; path: string | null; icon: React.ReactNode }) {
  const handleOpen = () => {
    if (path && isElectron) {
      window.electronAPI.openFolder(path.split('/').slice(0, -1).join('/'))
    }
  }

  return (
    <button
      onClick={handleOpen}
      disabled={!path}
      className={`
        p-4 rounded-lg text-center transition-all
        ${path ? 'bg-da-success/10 border border-da-success/30 hover:bg-da-success/20 cursor-pointer' : 'bg-da-light/50 border border-da-light cursor-not-allowed opacity-50'}
      `}
    >
      <div className={`mx-auto mb-2 ${path ? 'text-da-success' : 'text-da-text-muted'}`}>
        {icon}
      </div>
      <div className="text-sm font-medium">{label}</div>
      <div className="text-xs text-da-text-muted mt-1">
        {path ? 'Ready' : 'Pending'}
      </div>
    </button>
  )
}


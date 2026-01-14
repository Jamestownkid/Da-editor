/**
 * Da Editor - Sidebar Component (v2)
 * ====================================
 * the job queue lives here
 * shows all jobs with their status
 * 
 * UX IMPROVEMENTS:
 * - New Job button for quick access
 * - Job search/filter
 * - Estimated time remaining
 * - Compact view toggle
 * - Drag to reorder (future)
 */

import React, { useState } from 'react'
import { Job } from '../types'

interface SidebarProps {
  jobs: Job[]
  selectedJob: Job | null
  onSelectJob: (job: Job | null) => void
  onResume: () => void
  isProcessing: boolean
  currentJobId: string | null
  onNewJob: () => void  // NEW: callback to go to new job view
}

export default function Sidebar({ jobs, selectedJob, onSelectJob, onResume, isProcessing, currentJobId, onNewJob }: SidebarProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [showCompact, setShowCompact] = useState(false)

  // 1a. count jobs by status for the header
  const pendingCount = jobs.filter(j => j.status === 'pending').length
  const runningCount = jobs.filter(j => j.status === 'running').length
  const doneCount = jobs.filter(j => j.status === 'done').length
  const errorCount = jobs.filter(j => j.status === 'error').length

  // filter jobs by search term
  const filteredJobs = searchTerm 
    ? jobs.filter(j => j.id.toLowerCase().includes(searchTerm.toLowerCase()))
    : jobs

  // estimate time remaining (rough calculation)
  const estimatedMinutes = pendingCount * 5 + (runningCount > 0 ? 3 : 0)

  return (
    <aside className="w-72 bg-da-dark flex flex-col border-r border-da-light/30">
      {/* 1b. logo and title */}
      <div className="p-6 border-b border-da-light/30">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-da-pink flex items-center justify-center cursor-pointer hover:scale-105 transition-transform" onClick={onNewJob}>
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-da-pink">DA EDITOR</h1>
            <p className="text-xs text-da-text-muted">b-roll automation</p>
          </div>
        </div>

        {/* NEW: quick new job button */}
        <button
          onClick={onNewJob}
          className="w-full btn-secondary flex items-center justify-center gap-2 mb-3"
          title="Create a new job (Ctrl+N)"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Job
        </button>

        {/* 1c. resume button */}
        <button
          onClick={onResume}
          disabled={isProcessing || pendingCount + errorCount === 0}
          className="w-full btn-primary flex items-center justify-center gap-2"
          title={isProcessing ? "Processing..." : "Resume all pending jobs"}
        >
          {isProcessing ? (
            <>
              <span className="animate-spin">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </span>
              Processing...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Resume Jobs
            </>
          )}
        </button>

        {/* estimated time remaining */}
        {pendingCount > 0 && (
          <div className="mt-3 text-xs text-da-text-muted text-center">
            ~{estimatedMinutes} min remaining for {pendingCount} job{pendingCount !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* 2a. status summary with tooltips */}
      <div className="px-4 py-3 flex gap-2 border-b border-da-light/20">
        <span className="badge-pending" title="Pending jobs waiting in queue">{pendingCount}</span>
        <span className="badge-running" title="Currently processing">{runningCount}</span>
        <span className="badge-done" title="Completed jobs">{doneCount}</span>
        {errorCount > 0 && <span className="badge-error" title="Jobs with errors - click Resume to retry">{errorCount}</span>}
      </div>

      {/* 2b. search and view controls */}
      <div className="px-4 py-3 space-y-2">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-da-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="Search jobs..."
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-da-medium rounded-lg border border-da-light/30 focus:border-da-pink focus:outline-none"
            />
          </div>
          <button 
            onClick={() => setShowCompact(!showCompact)}
            className={`p-2 rounded-lg transition-all ${showCompact ? 'bg-da-pink/20 text-da-pink' : 'bg-da-medium text-da-text-muted hover:text-da-text'}`}
            title="Toggle compact view"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h8m-8 6h16" />
            </svg>
          </button>
        </div>
        <h2 className="text-xs font-semibold text-da-text-muted uppercase tracking-wider">
          Jobs Queue ({filteredJobs.length}{searchTerm ? ` / ${jobs.length}` : ''})
        </h2>
      </div>

      {/* 3a. scrollable jobs list - with always visible scrollbar */}
      <div className="flex-1 overflow-y-scroll px-3 pb-4 scrollbar-always-show">
        {filteredJobs.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-da-light flex items-center justify-center">
              <svg className="w-8 h-8 text-da-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <p className="text-da-text-muted text-sm">{searchTerm ? 'No jobs match search' : 'No jobs yet'}</p>
            <p className="text-da-text-muted text-xs mt-1">{searchTerm ? 'Try a different search term' : 'Paste links to get started'}</p>
          </div>
        ) : (
          <div className={`space-y-${showCompact ? '1' : '2'}`}>
            {filteredJobs.map(job => (
              <JobCard
                key={job.id}
                job={job}
                isSelected={selectedJob?.id === job.id}
                isRunning={currentJobId === job.id}
                onClick={() => onSelectJob(job)}
                compact={showCompact}
              />
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}

// 4a. individual job card component - with compact mode support
interface JobCardProps {
  job: Job
  isSelected: boolean
  isRunning: boolean
  onClick: () => void
  compact?: boolean
}

function JobCard({ job, isSelected, isRunning, onClick, compact = false }: JobCardProps) {
  // status badge based on job status
  const statusBadge = {
    pending: <span className="badge-pending"><span className="w-1.5 h-1.5 rounded-full bg-da-warning"></span>{!compact && ' Pending'}</span>,
    running: <span className="badge-running"><span className="w-1.5 h-1.5 rounded-full bg-da-pink animate-pulse"></span>{!compact && ' Running'}</span>,
    done: <span className="badge-done"><span className="w-1.5 h-1.5 rounded-full bg-da-success"></span>{!compact && ' Done'}</span>,
    error: <span className="badge-error"><span className="w-1.5 h-1.5 rounded-full bg-da-error"></span>{!compact && ' Error'}</span>,
    paused: <span className="badge-paused"><span className="w-1.5 h-1.5 rounded-full bg-da-text-muted"></span>{!compact && ' Paused'}</span>,
  }[job.status]

  // format time for compact view
  const timeAgo = formatTimeAgo(job.created)

  return (
    <button
      onClick={onClick}
      title={`${job.id} - ${job.status} - ${job.links?.length || 0} links`}
      className={`
        w-full text-left ${compact ? 'p-2' : 'p-3'} rounded-lg transition-all
        ${isSelected ? 'bg-da-pink/20 border border-da-pink/50' : 'bg-da-medium hover:bg-da-light border border-transparent'}
        ${isRunning ? 'ring-2 ring-da-pink ring-offset-2 ring-offset-da-dark' : ''}
      `}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className={`font-medium ${compact ? 'text-xs' : 'text-sm'} truncate flex-1`}>{job.id}</span>
        {statusBadge}
      </div>
      
      {!compact && (
        <div className="text-xs text-da-text-muted flex items-center justify-between">
          <span>{job.links?.length || 0} link{(job.links?.length || 0) !== 1 ? 's' : ''}</span>
          <span>{timeAgo}</span>
        </div>
      )}

      {/* progress bar for running jobs */}
      {isRunning && (
        <div className="mt-2 progress-bar">
          <div className="progress-bar-fill shimmer" style={{ width: `${job.progress || 0}%` }} />
        </div>
      )}
    </button>
  )
}

// helper to format relative time
function formatTimeAgo(dateString: string): string {
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  } catch {
    return ''
  }
}


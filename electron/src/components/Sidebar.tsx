/**
 * Da Editor - Sidebar Component
 * ===============================
 * the job queue lives here
 * shows all jobs with their status
 * 
 * its like a todo list but for video processing
 */

import React from 'react'
import { Job } from '../types'

interface SidebarProps {
  jobs: Job[]
  selectedJob: Job | null
  onSelectJob: (job: Job | null) => void
  onResume: () => void
  isProcessing: boolean
  currentJobId: string | null
}

export default function Sidebar({ jobs, selectedJob, onSelectJob, onResume, isProcessing, currentJobId }: SidebarProps) {
  // 1a. count jobs by status for the header
  const pendingCount = jobs.filter(j => j.status === 'pending').length
  const runningCount = jobs.filter(j => j.status === 'running').length
  const doneCount = jobs.filter(j => j.status === 'done').length
  const errorCount = jobs.filter(j => j.status === 'error').length

  return (
    <aside className="w-72 bg-da-dark flex flex-col border-r border-da-light/30">
      {/* 1b. logo and title */}
      <div className="p-6 border-b border-da-light/30">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-da-pink flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-da-pink">DA EDITOR</h1>
            <p className="text-xs text-da-text-muted">b-roll automation</p>
          </div>
        </div>

        {/* 1c. resume button */}
        <button
          onClick={onResume}
          disabled={isProcessing || pendingCount + errorCount === 0}
          className="w-full btn-primary flex items-center justify-center gap-2"
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
      </div>

      {/* 2a. status summary */}
      <div className="px-4 py-3 flex gap-2 border-b border-da-light/20">
        <span className="badge-pending">{pendingCount}</span>
        <span className="badge-running">{runningCount}</span>
        <span className="badge-done">{doneCount}</span>
        {errorCount > 0 && <span className="badge-error">{errorCount}</span>}
      </div>

      {/* 2b. jobs list header */}
      <div className="px-4 py-3">
        <h2 className="text-xs font-semibold text-da-text-muted uppercase tracking-wider">
          Jobs Queue ({jobs.length})
        </h2>
      </div>

      {/* 3a. scrollable jobs list */}
      <div className="flex-1 overflow-y-auto px-3 pb-4">
        {jobs.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-da-light flex items-center justify-center">
              <svg className="w-8 h-8 text-da-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <p className="text-da-text-muted text-sm">No jobs yet</p>
            <p className="text-da-text-muted text-xs mt-1">Paste links to get started</p>
          </div>
        ) : (
          <div className="space-y-2">
            {jobs.map(job => (
              <JobCard
                key={job.id}
                job={job}
                isSelected={selectedJob?.id === job.id}
                isRunning={currentJobId === job.id}
                onClick={() => onSelectJob(job)}
              />
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}

// 4a. individual job card component
interface JobCardProps {
  job: Job
  isSelected: boolean
  isRunning: boolean
  onClick: () => void
}

function JobCard({ job, isSelected, isRunning, onClick }: JobCardProps) {
  // status badge based on job status
  const statusBadge = {
    pending: <span className="badge-pending"><span className="w-1.5 h-1.5 rounded-full bg-da-warning"></span> Pending</span>,
    running: <span className="badge-running"><span className="w-1.5 h-1.5 rounded-full bg-da-pink animate-pulse"></span> Running</span>,
    done: <span className="badge-done"><span className="w-1.5 h-1.5 rounded-full bg-da-success"></span> Done</span>,
    error: <span className="badge-error"><span className="w-1.5 h-1.5 rounded-full bg-da-error"></span> Error</span>,
    paused: <span className="badge-paused"><span className="w-1.5 h-1.5 rounded-full bg-da-text-muted"></span> Paused</span>,
  }[job.status]

  return (
    <button
      onClick={onClick}
      className={`
        w-full text-left p-3 rounded-lg transition-all
        ${isSelected ? 'bg-da-pink/20 border border-da-pink/50' : 'bg-da-medium hover:bg-da-light border border-transparent'}
        ${isRunning ? 'ring-2 ring-da-pink ring-offset-2 ring-offset-da-dark' : ''}
      `}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="font-medium text-sm truncate flex-1">{job.id}</span>
        {statusBadge}
      </div>
      
      <div className="text-xs text-da-text-muted">
        {job.links.length} link{job.links.length !== 1 ? 's' : ''}
      </div>

      {/* progress bar for running jobs */}
      {isRunning && (
        <div className="mt-2 progress-bar">
          <div className="progress-bar-fill shimmer" style={{ width: `${job.progress}%` }} />
        </div>
      )}
    </button>
  )
}


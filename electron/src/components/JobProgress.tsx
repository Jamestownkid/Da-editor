/**
 * Job Progress Capsules Component
 * ================================
 * Shows 10 color-coded capsules for job progress
 * Like a soccer formation - visual status at a glance
 */

import React from 'react'

interface Step {
  id: string
  name: string
  status: 'pending' | 'running' | 'done' | 'failed' | 'skipped'
  estTime?: string
  actualTime?: string
}

interface JobProgressProps {
  steps: Step[]
  compact?: boolean
}

const STEP_COLORS = {
  pending: { bg: 'bg-gray-700', fill: 'bg-gray-500', text: 'text-gray-400' },
  running: { bg: 'bg-blue-900', fill: 'bg-blue-500 animate-pulse', text: 'text-blue-300' },
  done: { bg: 'bg-green-900', fill: 'bg-green-500', text: 'text-green-300' },
  failed: { bg: 'bg-red-900', fill: 'bg-red-500', text: 'text-red-300' },
  skipped: { bg: 'bg-yellow-900', fill: 'bg-yellow-500', text: 'text-yellow-300' },
}

const STEP_ICONS: Record<string, string> = {
  validate: '✓',
  download: '⬇',
  srt: '📝',
  keywords: '🔑',
  scrape: '🖼',
  render_landscape: '🎬',
  render_portrait: '📱',
  render_youtube: '▶',
  sfx: '🔊',
  cleanup: '🧹',
}

export default function JobProgress({ steps, compact = false }: JobProgressProps) {
  if (!steps || steps.length === 0) {
    return null
  }

  // Calculate overall progress
  const doneCount = steps.filter(s => s.status === 'done').length
  const totalSteps = steps.length
  const progressPercent = Math.round((doneCount / totalSteps) * 100)

  return (
    <div className="bg-da-medium rounded-xl p-4 border border-da-light/20">
      {/* Header with overall progress */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-white">Job Progress</span>
        <span className="text-xs text-da-text-muted">{progressPercent}% ({doneCount}/{totalSteps})</span>
      </div>

      {/* Capsules Grid */}
      <div className={`grid ${compact ? 'grid-cols-5' : 'grid-cols-5'} gap-2`}>
        {steps.map((step, index) => {
          const colors = STEP_COLORS[step.status]
          const icon = STEP_ICONS[step.id] || '○'
          
          return (
            <div
              key={step.id}
              className={`relative rounded-lg p-2 ${colors.bg} border border-${step.status === 'failed' ? 'red' : step.status === 'done' ? 'green' : 'gray'}-500/30 transition-all duration-300 hover:scale-105 cursor-pointer group`}
              title={`${step.name}: ${step.status}${step.actualTime ? ` (${step.actualTime})` : ''}`}
            >
              {/* Progress fill bar */}
              <div className="absolute bottom-0 left-0 right-0 h-1 rounded-b-lg overflow-hidden bg-black/30">
                <div 
                  className={`h-full ${colors.fill} transition-all duration-500`}
                  style={{ width: step.status === 'done' ? '100%' : step.status === 'running' ? '50%' : '0%' }}
                />
              </div>

              {/* Icon */}
              <div className="text-center">
                <span className="text-lg">{icon}</span>
              </div>

              {/* Step name (abbreviated) */}
              <div className={`text-center text-xs ${colors.text} font-medium truncate`}>
                {step.name.slice(0, 8)}
              </div>

              {/* Time display */}
              {step.actualTime && (
                <div className="text-center text-xs text-da-text-muted mt-1">
                  {step.actualTime}
                </div>
              )}

              {/* Status indicator */}
              {step.status === 'running' && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full animate-ping" />
              )}
              {step.status === 'failed' && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full flex items-center justify-center text-white text-xs">!</div>
              )}
            </div>
          )
        })}
      </div>

      {/* Legend (only in non-compact mode) */}
      {!compact && (
        <div className="flex items-center justify-center gap-4 mt-3 text-xs text-da-text-muted">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-gray-500" /> Pending
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" /> Running
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500" /> Done
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" /> Failed
          </span>
        </div>
      )}
    </div>
  )
}

// Default steps for a job
export const DEFAULT_JOB_STEPS: Step[] = [
  { id: 'validate', name: 'Validate', status: 'pending' },
  { id: 'download', name: 'Download', status: 'pending' },
  { id: 'srt', name: 'SRT', status: 'pending' },
  { id: 'keywords', name: 'Keywords', status: 'pending' },
  { id: 'scrape', name: 'Scrape', status: 'pending' },
  { id: 'render_landscape', name: 'Landscape', status: 'pending' },
  { id: 'render_portrait', name: 'Portrait', status: 'pending' },
  { id: 'render_youtube', name: 'YouTube', status: 'pending' },
  { id: 'sfx', name: 'SFX', status: 'pending' },
  { id: 'cleanup', name: 'Cleanup', status: 'pending' },
]

// Parse timeline.json to steps
export function parseTimeline(timeline: any): Step[] {
  const steps = [...DEFAULT_JOB_STEPS]
  
  if (!timeline || !timeline.steps) {
    return steps
  }

  const summary = timeline.summary || {}
  
  // Update steps based on timeline
  for (const entry of timeline.steps) {
    const stepId = entry.step
    const step = steps.find(s => s.id === stepId || s.id.startsWith(stepId.split('_')[0]))
    
    if (step) {
      if (entry.status === 'done') {
        step.status = 'done'
        step.actualTime = summary[stepId] || entry.elapsed_display
      } else if (entry.status === 'start') {
        if (step.status !== 'done') {
          step.status = 'running'
        }
      }
    }
  }

  return steps
}


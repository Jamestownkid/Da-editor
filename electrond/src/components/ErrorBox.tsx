/**
 * Da Editor - Error Box Component
 * ================================
 * displays errors in bottom left corner (rule 109)
 * one-click copy for debugging
 * shows both errors and background logs
 */

import { useState } from 'react'

interface ErrorBoxProps {
  errors: string[]
  logs: string[]
  onClose: () => void
  onClear: () => void
}

export default function ErrorBox({ errors, logs, onClose, onClear }: ErrorBoxProps) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  // copy all data - errors + logs + system info
  const handleCopyAll = async () => {
    const systemInfo = {
      timestamp: new Date().toISOString(),
      platform: navigator.platform,
      userAgent: navigator.userAgent,
    }
    
    const data = `=== DA EDITOR ERROR REPORT ===
Generated: ${systemInfo.timestamp}
Platform: ${systemInfo.platform}

=== ERRORS (${errors.length}) ===
${errors.join('\n')}

=== RECENT LOGS (${logs.length}) ===
${logs.slice(-50).join('\n')}
`
    
    try {
      await navigator.clipboard.writeText(data)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (e) {
      // fallback
      const textarea = document.createElement('textarea')
      textarea.value = data
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (!expanded) {
    // collapsed state - just a small badge in corner
    return (
      <div className="fixed bottom-4 left-4 z-50">
        <button
          onClick={() => setExpanded(true)}
          className="flex items-center gap-2 px-4 py-2 bg-da-error/90 text-white rounded-lg shadow-lg hover:bg-da-error transition-all animate-pulse"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="font-bold">{errors.length} Error{errors.length !== 1 ? 's' : ''}</span>
        </button>
      </div>
    )
  }

  // expanded state - full error panel
  return (
    <div className="fixed bottom-4 left-4 z-50 w-96 max-h-[60vh] bg-da-dark border border-da-error/50 rounded-xl shadow-2xl overflow-hidden flex flex-col">
      {/* header */}
      <div className="p-3 bg-da-error/20 border-b border-da-error/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-da-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="font-bold text-da-error">Errors ({errors.length})</span>
        </div>
        
        <div className="flex items-center gap-1">
          <button
            onClick={() => setExpanded(false)}
            className="p-1 hover:bg-da-light rounded"
            title="Minimize"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 12H6" />
            </svg>
          </button>
          <button
            onClick={onClose}
            className="p-1 hover:bg-da-light rounded"
            title="Close"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* error list */}
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {errors.length === 0 ? (
          <div className="text-center py-4 text-da-text-muted">
            No errors
          </div>
        ) : (
          errors.map((err, i) => (
            <div key={i} className="p-2 bg-da-medium rounded text-xs font-mono text-da-error/90 break-words">
              {err}
            </div>
          ))
        )}
      </div>

      {/* actions */}
      <div className="p-3 border-t border-da-light/30 flex gap-2">
        <button
          onClick={handleCopyAll}
          className="flex-1 btn-primary text-sm flex items-center justify-center gap-2"
        >
          {copied ? (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Copied!
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
              Copy All (Errors + Logs)
            </>
          )}
        </button>
        
        <button
          onClick={onClear}
          className="btn-secondary text-sm px-3"
          title="Clear all errors"
        >
          Clear
        </button>
      </div>
    </div>
  )
}


/**
 * Da Editor - Top Bar Component
 * ===============================
 * the draggable header with controls
 * settings, quick actions, status indicator
 * 
 * keeping things accessible up top
 */

import React, { useState } from 'react'

interface TopBarProps {
  isProcessing: boolean
  currentJobId: string | null
  onOpenSettings: () => void
  onScanJobs: () => void
  onOpenOutput: () => void
}

export default function TopBar({ isProcessing, currentJobId, onOpenSettings, onScanJobs, onOpenOutput }: TopBarProps) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <header className="h-14 bg-da-dark border-b border-da-light/20 flex items-center justify-between px-4 drag-handle">
      {/* 1a. left side - menu dropdown */}
      <div className="flex items-center gap-3 no-drag">
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="btn-ghost flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            Quick Actions
            <svg className={`w-4 h-4 transition-transform ${menuOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* dropdown menu */}
          {menuOpen && (
            <div className="absolute top-full left-0 mt-1 w-48 bg-da-medium rounded-lg shadow-lg border border-da-light/30 py-1 z-50">
              <button
                onClick={() => { onScanJobs(); setMenuOpen(false) }}
                className="w-full px-4 py-2 text-left text-sm hover:bg-da-light flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Scan for Jobs
              </button>
              <button
                onClick={() => { onOpenOutput(); setMenuOpen(false) }}
                className="w-full px-4 py-2 text-left text-sm hover:bg-da-light flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
                </svg>
                Open Output Folder
              </button>
              <div className="border-t border-da-light/30 my-1" />
              <button
                onClick={() => setMenuOpen(false)}
                className="w-full px-4 py-2 text-left text-sm hover:bg-da-light flex items-center gap-2 text-da-error"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Clear Completed
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 1b. center - status indicator */}
      <div className="flex items-center gap-2">
        {isProcessing ? (
          <>
            <span className="w-2 h-2 rounded-full bg-da-pink animate-pulse" />
            <span className="text-sm text-da-pink font-medium">
              Processing: {currentJobId}
            </span>
          </>
        ) : (
          <>
            <span className="w-2 h-2 rounded-full bg-da-success" />
            <span className="text-sm text-da-success font-medium">Ready</span>
          </>
        )}
      </div>

      {/* 1c. right side - settings button */}
      <div className="flex items-center gap-3 no-drag">
        <button
          onClick={onOpenSettings}
          className="btn-ghost flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Settings
        </button>

        {/* window controls for non-mac */}
        {navigator.platform.toLowerCase().includes('win') && (
          <div className="flex items-center gap-1 ml-4">
            <button className="w-8 h-8 hover:bg-da-light rounded flex items-center justify-center">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M20 14H4v-2h16" />
              </svg>
            </button>
            <button className="w-8 h-8 hover:bg-da-light rounded flex items-center justify-center">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M4 4h16v16H4V4m2 2v12h12V6H6z" />
              </svg>
            </button>
            <button className="w-8 h-8 hover:bg-da-error rounded flex items-center justify-center">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* click outside to close menu */}
      {menuOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setMenuOpen(false)}
        />
      )}
    </header>
  )
}


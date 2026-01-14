/**
 * Da Editor - Main App Component
 * ================================
 * this is the whole app layout right here
 * sidebar on the left, main panel on the right
 * 
 * we keeping it clean and organized fr
 */

import React, { useState, useEffect, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import MainPanel from './components/MainPanel'
import TopBar from './components/TopBar'
import SettingsModal from './components/SettingsModal'
import Confetti from './components/Confetti'
import { Job, Settings, JobStatus } from './types'

// 1a. check if we in electron or browser
const isElectron = typeof window !== 'undefined' && window.electronAPI

export default function App() {
  // 2a. state management - keeping track of everything
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [settings, setSettings] = useState<Settings | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [showConfetti, setShowConfetti] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [errors, setErrors] = useState<string[]>([])

  // 2b. load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  // 2c. scan for existing jobs when settings load
  useEffect(() => {
    if (settings?.outputFolder) {
      scanForJobs()
    }
  }, [settings?.outputFolder])

  // 2d. listen for job progress events
  useEffect(() => {
    if (isElectron) {
      window.electronAPI.onJobProgress((msg: string) => {
        setLogs(prev => [...prev.slice(-100), `[${new Date().toLocaleTimeString()}] ${msg}`])
      })
      window.electronAPI.onJobError((msg: string) => {
        setErrors(prev => [...prev.slice(-50), `[${new Date().toLocaleTimeString()}] ${msg}`])
      })

      return () => {
        window.electronAPI.removeJobListeners()
      }
    }
  }, [])

  // 3a. load settings from electron store or localStorage
  const loadSettings = async () => {
    if (isElectron) {
      const s = await window.electronAPI.getSettings()
      setSettings(s)
    } else {
      // fallback for browser dev
      const stored = localStorage.getItem('da-editor-settings')
      if (stored) {
        setSettings(JSON.parse(stored))
      } else {
        setSettings({
          outputFolder: '',
          whisperModel: 'base',
          useGpu: true,
          bgColor: '#FFFFFF',
          soundsFolder: '',
          secondsPerImage: 4.0,
          soundVolume: 0.8,
          minImages: 15
        })
      }
    }
  }

  // 3b. save settings
  const saveSettings = async (newSettings: Settings) => {
    setSettings(newSettings)
    if (isElectron) {
      await window.electronAPI.saveSettings(newSettings)
    } else {
      localStorage.setItem('da-editor-settings', JSON.stringify(newSettings))
    }
  }

  // 4a. scan output folder for existing jobs
  const scanForJobs = async () => {
    if (!settings?.outputFolder) return

    if (isElectron) {
      const foundJobs = await window.electronAPI.scanJobs(settings.outputFolder)
      setJobs(foundJobs)
    }
  }

  // 4b. create a new job
  const createJob = useCallback(async (links: string[], jobName: string, options: { generateSrt: boolean; downloadVideos: boolean }) => {
    if (!settings?.outputFolder) {
      setErrors(prev => [...prev, 'yo set an output folder first in settings'])
      return
    }

    // create unique job id
    const timestamp = Date.now()
    const safeJobName = jobName || `job_${timestamp}`
    
    // create folder structure
    let jobFolder = ''
    if (isElectron) {
      jobFolder = await window.electronAPI.createJobFolder(settings.outputFolder, safeJobName)
    }

    // create job object
    const job: Job = {
      id: safeJobName,
      folder: jobFolder,
      created: new Date().toISOString(),
      links,
      generateSrt: options.generateSrt,
      downloadVideos: options.downloadVideos,
      status: 'pending',
      progress: 0,
      outputs: {
        slideshow: null,
        portrait: null,
        youtubeMix: null
      },
      settings: { ...settings }, // snapshot settings at job creation
      errors: [],
      downloadedVideos: [],
      srtFiles: [],
      keywords: [],
      images: []
    }

    // save job json
    if (isElectron && jobFolder) {
      await window.electronAPI.saveJob(jobFolder, job)
    }

    // add to state
    setJobs(prev => [...prev, job])

    // show confetti
    setShowConfetti(true)
    setTimeout(() => setShowConfetti(false), 2000)

    // start processing if nothing running
    if (!isProcessing) {
      processNextJob([...jobs, job])
    }
  }, [settings, jobs, isProcessing])

  // 5a. process the next pending job
  const processNextJob = async (jobList: Job[] = jobs) => {
    const pendingJob = jobList.find(j => j.status === 'pending')
    
    if (!pendingJob) {
      setIsProcessing(false)
      setCurrentJobId(null)
      return
    }

    setIsProcessing(true)
    setCurrentJobId(pendingJob.id)

    // update job status
    const updated = jobList.map(j => 
      j.id === pendingJob.id ? { ...j, status: 'running' as JobStatus } : j
    )
    setJobs(updated)

    // save updated status
    if (isElectron && pendingJob.folder) {
      await window.electronAPI.saveJob(pendingJob.folder, { ...pendingJob, status: 'running' })
    }

    try {
      // run the job via python backend
      if (isElectron) {
        await window.electronAPI.runJob(pendingJob.folder, pendingJob.settings || settings)
      } else {
        // simulate for browser dev
        await new Promise(resolve => setTimeout(resolve, 3000))
      }

      // mark as done
      setJobs(prev => prev.map(j => 
        j.id === pendingJob.id ? { ...j, status: 'done' as JobStatus, progress: 100 } : j
      ))

      if (isElectron && pendingJob.folder) {
        await window.electronAPI.saveJob(pendingJob.folder, { ...pendingJob, status: 'done', progress: 100 })
      }

    } catch (err: any) {
      // mark as error
      const errorMsg = err.message || 'unknown error'
      setJobs(prev => prev.map(j => 
        j.id === pendingJob.id ? { ...j, status: 'error' as JobStatus, errors: [...j.errors, errorMsg] } : j
      ))

      if (isElectron && pendingJob.folder) {
        await window.electronAPI.saveJob(pendingJob.folder, { 
          ...pendingJob, 
          status: 'error',
          errors: [...pendingJob.errors, errorMsg]
        })
      }
    }

    // process next in queue
    setTimeout(() => {
      const remaining = jobs.filter(j => j.id !== pendingJob.id)
      processNextJob(remaining)
    }, 500)
  }

  // 5b. resume all pending/paused jobs
  const resumeJobs = () => {
    const pending = jobs.filter(j => j.status === 'pending' || j.status === 'paused' || j.status === 'error')
    if (pending.length > 0 && !isProcessing) {
      // reset error jobs to pending
      const reset = jobs.map(j => 
        j.status === 'error' || j.status === 'paused' ? { ...j, status: 'pending' as JobStatus } : j
      )
      setJobs(reset)
      processNextJob(reset)
    }
  }

  // 5c. stop current job
  const stopCurrentJob = async () => {
    if (isElectron && isProcessing) {
      await window.electronAPI.stopJob()
      setIsProcessing(false)
      
      // mark current job as paused
      if (currentJobId) {
        setJobs(prev => prev.map(j => 
          j.id === currentJobId ? { ...j, status: 'paused' as JobStatus } : j
        ))
      }
    }
  }

  // 6a. render the app
  return (
    <div className="h-screen flex flex-col bg-da-darker overflow-hidden">
      {/* top bar with drag handle and controls */}
      <TopBar 
        isProcessing={isProcessing}
        currentJobId={currentJobId}
        onOpenSettings={() => setShowSettings(true)}
        onScanJobs={scanForJobs}
        onOpenOutput={() => {
          if (isElectron && settings?.outputFolder) {
            window.electronAPI.openFolder(settings.outputFolder)
          }
        }}
      />

      {/* main content area */}
      <div className="flex-1 flex overflow-hidden">
        {/* sidebar with jobs list */}
        <Sidebar
          jobs={jobs}
          selectedJob={selectedJob}
          onSelectJob={setSelectedJob}
          onResume={resumeJobs}
          isProcessing={isProcessing}
          currentJobId={currentJobId}
        />

        {/* main panel */}
        <MainPanel
          settings={settings}
          selectedJob={selectedJob}
          onCreateJob={createJob}
          onStopJob={stopCurrentJob}
          isProcessing={isProcessing}
          logs={logs}
          errors={errors}
        />
      </div>

      {/* settings modal */}
      {showSettings && settings && (
        <SettingsModal
          settings={settings}
          onSave={saveSettings}
          onClose={() => setShowSettings(false)}
        />
      )}

      {/* confetti animation */}
      {showConfetti && <Confetti />}
    </div>
  )
}


/**
 * Da Editor - Main App Component (v3)
 * =====================================
 * FIXED:
 * - Resume now properly re-scans disk for all jobs
 * - Backend owns job.json after processing starts (no overwrites)
 * - Error box in bottom left with copy functionality
 * - Better state management for job queue
 */

import { useState, useEffect, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import MainPanel from './components/MainPanel'
import TopBar from './components/TopBar'
import SettingsModal from './components/SettingsModal'
import Confetti from './components/Confetti'
import ErrorBox from './components/ErrorBox'
import { Job, Settings, JobStatus, LinkItem } from './types'
import './global.d.ts'

const isElectron = typeof window !== 'undefined' && window.electronAPI

export default function App() {
  // state
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [settings, setSettings] = useState<Settings | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [showConfetti, setShowConfetti] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [showErrorBox, setShowErrorBox] = useState(true)
  const [systemStats, setSystemStats] = useState<{ cpu: number; ram: number; disk: number } | null>(null)

  // load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  // scan for existing jobs when settings load
  useEffect(() => {
    if (settings?.outputFolder) {
      scanForJobs()
    }
  }, [settings?.outputFolder])

  // KEYBOARD SHORTCUTS - UX improvement
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+N or Cmd+N = New Job (go home)
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault()
        goHome()
      }
      // Ctrl+S or Cmd+S = Open Settings
      if ((e.ctrlKey || e.metaKey) && e.key === 's' && !e.shiftKey) {
        e.preventDefault()
        setShowSettings(true)
      }
      // Escape = Close modals or deselect job
      if (e.key === 'Escape') {
        if (showSettings) {
          setShowSettings(false)
        } else if (selectedJob) {
          setSelectedJob(null)
        }
      }
      // Ctrl+R or Cmd+R = Resume jobs (if not already processing)
      if ((e.ctrlKey || e.metaKey) && e.key === 'r' && !isProcessing) {
        e.preventDefault()
        resumeJobs()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [showSettings, selectedJob, isProcessing])

  // poll system stats when processing - helps user know if PC is struggling
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    
    if (isProcessing && isElectron) {
      // poll every 2 seconds
      interval = setInterval(async () => {
        try {
          const stats = await window.electronAPI.getSystemStats()
          setSystemStats(stats)
          
          // SAFEGUARD: warn user if resources are critical
          if (stats.cpu > 95 || stats.ram > 95) {
            setErrors((prev: string[]) => {
              // only add warning once
              const warningExists = prev.some(e => e.includes('SYSTEM OVERLOAD'))
              if (!warningExists) {
                return [...prev, `WARNING: SYSTEM OVERLOAD - CPU: ${stats.cpu}%, RAM: ${stats.ram}%. Consider pausing jobs.`]
              }
              return prev
            })
          }
        } catch (e) {
          // ignore stats errors
        }
      }, 2000)
    } else {
      setSystemStats(null)
    }
    
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isProcessing])

  // listen for job progress events
  useEffect(() => {
    if (isElectron) {
      window.electronAPI.onJobProgress((msg: string) => {
        setLogs((prev: string[]) => [...prev.slice(-100), msg])
      })
      window.electronAPI.onJobError((msg: string) => {
        // FILTER: whisper progress bars are NOT errors - they're just stderr output
        // skip anything that looks like a progress bar (%|█ etc)
        if (msg.includes('%|') || msg.includes('frames/s') || msg.includes('█')) {
          // this is just whisper progress, not an error - add to logs instead
          setLogs((prev: string[]) => [...prev.slice(-100), msg])
          return
        }
        setErrors((prev: string[]) => [...prev.slice(-50), msg])
      })

      return () => {
        window.electronAPI.removeJobListeners()
      }
    }
  }, [])

  // load settings
  const loadSettings = async () => {
    if (isElectron) {
      const s = await window.electronAPI.getSettings()
      setSettings(s)
    } else {
      const stored = localStorage.getItem('da-editor-settings')
      if (stored) {
        setSettings(JSON.parse(stored))
      } else {
        setSettings({
          outputFolder: '',
          whisperModel: 'medium',  // default to medium per user request
          useGpu: true,
          bgColor: '#FFFFFF',
          soundsFolder: '',
          secondsPerImage: 4.0,
          soundVolume: 1.0,  // rule 42 - boosted
          minImages: 12
        })
      }
    }
  }

  // save settings
  const saveSettings = async (newSettings: Settings) => {
    setSettings(newSettings)
    if (isElectron) {
      await window.electronAPI.saveSettings(newSettings)
    } else {
      localStorage.setItem('da-editor-settings', JSON.stringify(newSettings))
    }
  }

  // scan for existing jobs
  const scanForJobs = async () => {
    if (!settings?.outputFolder) return

    if (isElectron) {
      const foundJobs = await window.electronAPI.scanJobs(settings.outputFolder)
      setJobs(foundJobs)
    }
  }

  // create a new job with per-link toggles
  const createJob = useCallback(async (links: LinkItem[], jobName: string) => {
    if (!settings?.outputFolder) {
      setErrors((prev: string[]) => [...prev, 'set an output folder first in settings yo'])
      return
    }

    // create unique job id
    const timestamp = Date.now()
    const randomId = Math.floor(Math.random() * 1000)
    const safeJobName = jobName || `job_${timestamp}_${randomId}`
    
    // create folder
    let jobFolder = ''
    if (isElectron) {
      jobFolder = await window.electronAPI.createJobFolder(settings.outputFolder, safeJobName)
    }

    // create job object matching expected structure
    const job: Job = {
      id: safeJobName,
      topic: safeJobName,
      folder: jobFolder,
      created: new Date().toISOString(),
      created_at: new Date().toISOString(),
      urls: links,  // new format with per-link toggles
      links: links.map(l => l.url),  // backwards compat
      status: 'pending',
      progress: 0,
      outputs: {
        slideshow: null,
        portrait: null,
        youtubeMix: null
      },
      settings: { ...settings },
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
    setJobs((prev: Job[]) => [...prev, job])

    // show confetti
    setShowConfetti(true)
    setTimeout(() => setShowConfetti(false), 2500)

    // start processing
    if (!isProcessing) {
      processNextJob([...jobs, job])
    }
  }, [settings, jobs, isProcessing])

  // process next pending job - WITH SAFEGUARDS
  const processNextJob = async (jobList: Job[] = jobs) => {
    const pendingJob = jobList.find(j => j.status === 'pending')
    
    if (!pendingJob) {
      setIsProcessing(false)
      setCurrentJobId(null)
      return
    }

    // SAFEGUARD: check system resources before starting
    if (isElectron) {
      try {
        const sysCheck = await window.electronAPI.checkSystem()
        if (!sysCheck.safe) {
          const issues: string[] = []
          if (sysCheck.disk !== 'OK') issues.push(`Disk: ${sysCheck.disk}`)
          if (sysCheck.memory !== 'OK') issues.push(`Memory: ${sysCheck.memory}`)
          if (sysCheck.cpu !== 'OK') issues.push(`CPU: ${sysCheck.cpu}`)
          
          setErrors((prev: string[]) => [
            ...prev, 
            `SYSTEM WARNING: ${issues.join(', ')}. Job may fail or crash. Free up resources before continuing.`
          ])
          
          // still proceed but user is warned
        }
      } catch (e) {
        // ignore check failure, proceed anyway
      }
    }

    setIsProcessing(true)
    setCurrentJobId(pendingJob.id)
    setLogs([])  // clear logs for new job

    // update status
    const updated = jobList.map(j => 
      j.id === pendingJob.id ? { ...j, status: 'running' as JobStatus } : j
    )
    setJobs(updated)

    if (isElectron && pendingJob.folder) {
      await window.electronAPI.saveJob(pendingJob.folder, { ...pendingJob, status: 'running' })
    }

    try {
      if (isElectron && settings) {
        await window.electronAPI.runJob(pendingJob.folder!, pendingJob.settings || settings)
      } else if (!isElectron) {
        await new Promise(resolve => setTimeout(resolve, 3000))
      }

      // FIXED: re-read job.json from disk instead of overwriting
      // backend (Python) owns the job.json after processing
      if (isElectron && pendingJob.folder) {
        const updatedJob = await window.electronAPI.readJob(pendingJob.folder)
        if (updatedJob) {
          setJobs((prev: Job[]) => prev.map((j: Job) => 
            j.id === pendingJob.id ? { ...updatedJob, folder: pendingJob.folder } : j
          ))
        } else {
          // fallback if read fails
          setJobs((prev: Job[]) => prev.map((j: Job) => 
            j.id === pendingJob.id ? { ...j, status: 'done' as JobStatus, progress: 100 } : j
          ))
        }
      } else {
        setJobs((prev: Job[]) => prev.map((j: Job) => 
          j.id === pendingJob.id ? { ...j, status: 'done' as JobStatus, progress: 100 } : j
        ))
      }

    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'unknown error'
      setErrors((prev: string[]) => [...prev, `Job ${pendingJob.id} failed: ${errorMsg}`])
      
      // re-read job from disk to get actual state
      if (isElectron && pendingJob.folder) {
        const updatedJob = await window.electronAPI.readJob(pendingJob.folder)
        if (updatedJob) {
          setJobs((prev: Job[]) => prev.map((j: Job) => 
            j.id === pendingJob.id ? { ...updatedJob, folder: pendingJob.folder, status: 'error' as JobStatus } : j
          ))
        } else {
          setJobs((prev: Job[]) => prev.map((j: Job) => 
            j.id === pendingJob.id ? { ...j, status: 'error' as JobStatus, errors: [...j.errors, errorMsg] } : j
          ))
        }
      }
    }

    // process next
    setTimeout(() => processNextJob(), 500)
  }

  // resume jobs - FIXED: re-scan disk first to get ALL jobs
  const resumeJobs = async () => {
    if (isProcessing) return
    
    // first, re-scan disk to get all jobs (including ones from previous sessions)
    if (isElectron && settings?.outputFolder) {
      const diskJobs = await window.electronAPI.scanJobs(settings.outputFolder)
      
      // merge with current jobs, preferring disk versions
      const mergedJobs = diskJobs.map((diskJob: Job) => {
        // if job was error/paused, reset to pending for retry
        if (diskJob.status === 'error' || diskJob.status === 'paused') {
          return { ...diskJob, status: 'pending' as JobStatus }
        }
        // if job says "running" but we're not processing, it crashed - reset to pending
        if (diskJob.status === 'running') {
          return { ...diskJob, status: 'pending' as JobStatus }
        }
        return diskJob
      })
      
      setJobs(mergedJobs)
      
      // start processing if there are pending jobs
      const pendingJobs = mergedJobs.filter((j: Job) => j.status === 'pending')
      if (pendingJobs.length > 0) {
        processNextJob(mergedJobs)
      }
    } else {
      // fallback to in-memory jobs
      const pending = jobs.filter((j: Job) => j.status === 'pending' || j.status === 'paused' || j.status === 'error')
      if (pending.length > 0) {
        const reset = jobs.map((j: Job) => 
          j.status === 'error' || j.status === 'paused' || j.status === 'running' 
            ? { ...j, status: 'pending' as JobStatus } : j
        )
        setJobs(reset)
        processNextJob(reset)
      }
    }
  }

  // stop current job
  const stopCurrentJob = async () => {
    if (isElectron && isProcessing) {
      await window.electronAPI.stopJob()
      setIsProcessing(false)
      
      if (currentJobId) {
        setJobs((prev: Job[]) => prev.map((j: Job) => 
          j.id === currentJobId ? { ...j, status: 'paused' as JobStatus } : j
        ))
      }
    }
  }

  // GO HOME - deselect job and show new job form
  const goHome = () => {
    setSelectedJob(null)
  }

  // clear completed jobs from UI (doesn't delete from disk)
  const clearCompletedJobs = () => {
    setJobs((prev: Job[]) => prev.filter((j: Job) => j.status !== 'done'))
  }

  // STOP A SPECIFIC JOB by ID
  const stopJobById = async (jobId: string) => {
    if (isElectron && currentJobId === jobId) {
      await window.electronAPI.stopJob()
      setIsProcessing(false)
      setCurrentJobId(null)
      
      setJobs((prev: Job[]) => prev.map((j: Job) => 
        j.id === jobId ? { ...j, status: 'paused' as JobStatus } : j
      ))
    }
  }

  // DELETE A JOB - removes from list and optionally deletes folder
  const deleteJob = async (jobId: string, deleteFolder: boolean) => {
    // if job is running, stop it first
    if (currentJobId === jobId) {
      await stopJobById(jobId)
    }
    
    // find job to get folder path
    const job = jobs.find(j => j.id === jobId)
    
    // remove from state
    setJobs((prev: Job[]) => prev.filter((j: Job) => j.id !== jobId))
    
    // deselect if selected
    if (selectedJob?.id === jobId) {
      setSelectedJob(null)
    }
    
    // delete folder if requested
    if (deleteFolder && job?.folder && isElectron) {
      try {
        await window.electronAPI.deleteFolder(job.folder)
      } catch (e) {
        console.error('failed to delete folder:', e)
      }
    }
  }

  // stop all jobs - emergency stop
  const stopAllJobs = async () => {
    if (isElectron && isProcessing) {
      await window.electronAPI.stopJob()
      setIsProcessing(false)
      setCurrentJobId(null)
      
      // pause all pending/running jobs
      setJobs((prev: Job[]) => prev.map((j: Job) => 
        j.status === 'pending' || j.status === 'running' 
          ? { ...j, status: 'paused' as JobStatus } 
          : j
      ))
    }
  }

  return (
    <div className="h-screen flex flex-col bg-da-darker overflow-hidden">
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
        onGoHome={goHome}
        onClearCompleted={clearCompletedJobs}
        onStopAllJobs={stopAllJobs}
        systemStats={systemStats}
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          jobs={jobs}
          selectedJob={selectedJob}
          onSelectJob={setSelectedJob}
          onResume={resumeJobs}
          onStopJob={stopJobById}
          onDeleteJob={deleteJob}
          isProcessing={isProcessing}
          currentJobId={currentJobId}
          onNewJob={goHome}
        />

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

      {showSettings && settings && (
        <SettingsModal
          settings={settings}
          onSave={saveSettings}
          onClose={() => setShowSettings(false)}
        />
      )}

      {showConfetti && <Confetti />}
      
      {/* Error box at bottom left - always visible when there are errors */}
      {showErrorBox && errors.length > 0 && (
        <ErrorBox 
          errors={errors} 
          logs={logs}
          onClose={() => setShowErrorBox(false)}
          onClear={() => setErrors([])}
        />
      )}
    </div>
  )
}

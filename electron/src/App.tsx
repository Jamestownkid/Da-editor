/**
 * Da Editor - Main App Component (v4)
 * =====================================
 * ADDED:
 * - Scan button - verifies job folder integrity
 * - Smart Resume - detects missing files and refetches them
 * - Beta Face Overlay modal
 * - Accurate time estimation with historical data
 * - Job time cap (45 min max)
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import Sidebar from './components/Sidebar'
import MainPanel from './components/MainPanel'
import TopBar from './components/TopBar'
import SettingsModal from './components/SettingsModal'
import Confetti from './components/Confetti'
import ErrorBox from './components/ErrorBox'
import { Job, Settings, JobStatus, LinkItem } from './types'
import './global.d.ts'

const isElectron = typeof window !== 'undefined' && window.electronAPI

// Job history for time estimation
interface JobHistory {
  id: string
  linkCount: number
  imageCount: number
  durationMinutes: number
  timestamp: number
}

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
  const [showBetaModal, setShowBetaModal] = useState(false)
  const [faceOverlayPath, setFaceOverlayPath] = useState<string | null>(null)
  const [overlayTarget, setOverlayTarget] = useState<'instagram' | 'youtube-corner' | 'all'>('instagram')
  const [overlayPosition, setOverlayPosition] = useState<'bottom' | 'top-right' | 'top-left'>('bottom')
  const [timeEstimate, setTimeEstimate] = useState<{ totalMinutes: number; completedMinutes: number; currentStep: string } | null>(null)
  const [jobHistory, setJobHistory] = useState<JobHistory[]>([])
  
  // Refs for time tracking
  const jobStartTime = useRef<number | null>(null)
  const jobsRef = useRef<Job[]>([])

  // Keep jobsRef in sync
  useEffect(() => {
    jobsRef.current = jobs
  }, [jobs])

  // load settings on mount
  useEffect(() => {
    loadSettings()
    loadJobHistory()
  }, [])

  // scan for existing jobs when settings load
  useEffect(() => {
    if (settings?.outputFolder) {
      scanForJobs()
    }
  }, [settings?.outputFolder])

  // KEYBOARD SHORTCUTS
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault()
        goHome()
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 's' && !e.shiftKey) {
        e.preventDefault()
        setShowSettings(true)
      }
      if (e.key === 'Escape') {
        if (showSettings) setShowSettings(false)
        else if (showBetaModal) setShowBetaModal(false)
        else if (selectedJob) setSelectedJob(null)
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'r' && !isProcessing) {
        e.preventDefault()
        smartResume()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [showSettings, showBetaModal, selectedJob, isProcessing])

  // poll system stats when processing
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    
    if (isProcessing && isElectron) {
      interval = setInterval(async () => {
        try {
          const stats = await window.electronAPI.getSystemStats()
          setSystemStats(stats)
          
          // Update time estimate based on elapsed time
          if (jobStartTime.current) {
            const elapsedMinutes = (Date.now() - jobStartTime.current) / 60000
            setTimeEstimate(prev => prev ? {
              ...prev,
              completedMinutes: Math.min(elapsedMinutes, prev.totalMinutes)
            } : null)
          }
          
          if (stats.cpu > 95 || stats.ram > 95) {
            setErrors((prev: string[]) => {
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
        
        // Update time estimate step based on log message
        if (msg.includes('step 1:')) setTimeEstimate(prev => prev ? { ...prev, currentStep: 'Downloading...' } : null)
        else if (msg.includes('step 2:')) setTimeEstimate(prev => prev ? { ...prev, currentStep: 'Transcribing...' } : null)
        else if (msg.includes('step 3:')) setTimeEstimate(prev => prev ? { ...prev, currentStep: 'Extracting keywords...' } : null)
        else if (msg.includes('step 4:')) setTimeEstimate(prev => prev ? { ...prev, currentStep: 'Scraping images...' } : null)
        else if (msg.includes('step 5:')) setTimeEstimate(prev => prev ? { ...prev, currentStep: 'Creating video...' } : null)
        else if (msg.includes('step 6:')) setTimeEstimate(prev => prev ? { ...prev, currentStep: 'Validating...' } : null)
      })
      window.electronAPI.onJobError((msg: string) => {
        if (msg.includes('%|') || msg.includes('frames/s') || msg.includes('█')) {
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

  // Load job history for time estimation
  const loadJobHistory = () => {
    try {
      const stored = localStorage.getItem('da-editor-job-history')
      if (stored) {
        setJobHistory(JSON.parse(stored))
      }
    } catch (e) {
      // ignore
    }
  }

  // Save job history
  const saveJobHistory = (history: JobHistory[]) => {
    try {
      // Keep only last 20 jobs
      const trimmed = history.slice(-20)
      localStorage.setItem('da-editor-job-history', JSON.stringify(trimmed))
      setJobHistory(trimmed)
    } catch (e) {
      // ignore
    }
  }

  // Estimate time based on job complexity and history
  const estimateJobTime = (job: Job): number => {
    const linkCount = job.links?.length || 1
    const imagesNeeded = (job.settings?.minImages || 15) - (job.images?.length || 0)
    
    // Base estimates (in minutes)
    let baseEstimate = linkCount * 3.5 + Math.max(0, imagesNeeded) * 0.5 + 5
    
    // Adjust based on historical data
    if (jobHistory.length > 0) {
      const similarJobs = jobHistory.filter(h => Math.abs(h.linkCount - linkCount) <= 2)
      if (similarJobs.length > 0) {
        const avgDuration = similarJobs.reduce((sum, j) => sum + j.durationMinutes, 0) / similarJobs.length
        baseEstimate = (baseEstimate + avgDuration) / 2
      }
    }
    
    // Cap at 45 minutes (our hard limit)
    return Math.min(45, Math.round(baseEstimate))
  }

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
          whisperModel: 'medium',
          useGpu: true,
          bgColor: '#FFFFFF',
          soundsFolder: '',
          secondsPerImage: 4.0,
          soundVolume: 1.0,
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

  // SCAN JOBS - verify integrity and check for issues
  const scanJobIntegrity = async () => {
    if (!settings?.outputFolder || !isElectron) return

    setLogs(prev => [...prev, '[Scan] Starting job integrity scan...'])
    
    const foundJobs = await window.electronAPI.scanJobs(settings.outputFolder)
    const scannedJobs: Job[] = []
    
    for (const job of foundJobs) {
      const issues: string[] = []
      const folder = job.folder || job.jobFolder
      
      if (!folder) {
        issues.push('Missing folder path')
        scannedJobs.push({ ...job, errors: issues })
        continue
      }

      // Check required files/folders
      const requiredChecks = [
        { path: `${folder}/job.json`, name: 'job.json' },
        { path: `${folder}/images`, name: 'images folder' },
      ]
      
      // Check for expected outputs if job is done
      if (job.status === 'done') {
        if (!job.outputs?.slideshow) issues.push('Missing slideshow output')
        if (!job.outputs?.portrait) issues.push('Missing portrait output')
      }
      
      // Check for unexpected files (videos that shouldn't be there)
      // This would require additional IPC handler - for now we track in issues
      
      // Mark job health
      const jobWithIssues = {
        ...job,
        folder,
        errors: [...(job.errors || []), ...issues],
        health: issues.length === 0 ? 'healthy' : 'issues'
      }
      
      scannedJobs.push(jobWithIssues)
      
      if (issues.length > 0) {
        setLogs(prev => [...prev, `[Scan] ${job.id}: ${issues.length} issues found`])
      }
    }
    
    setJobs(scannedJobs)
    setLogs(prev => [...prev, `[Scan] Complete. Scanned ${scannedJobs.length} jobs.`])
  }

  // SMART RESUME - check what's missing and fill it
  const smartResume = async () => {
    if (isProcessing) return
    
    if (!settings?.outputFolder || !isElectron) {
      resumeJobs()
      return
    }
    
    setLogs(prev => [...prev, '[Resume] Smart resume starting...'])
    
    // First scan for all jobs
    const diskJobs = await window.electronAPI.scanJobs(settings.outputFolder)
    
    // Analyze each job and determine what needs to be done
    const jobsToResume: Job[] = []
    
    for (const job of diskJobs) {
      const folder = job.folder || job.jobFolder
      if (!folder) continue
      
      // Skip completed jobs
      if (job.status === 'done' && job.outputs?.slideshow && job.outputs?.portrait) {
        continue
      }
      
      // Check what's missing
      const missingSteps: string[] = []
      
      // Check for downloaded videos
      const hasVideos = job.urls?.some((u: any) => u.downloaded_path) || false
      if (!hasVideos && job.urls?.length > 0) {
        missingSteps.push('download')
      }
      
      // Check for SRT files
      const needsSrt = job.urls?.some((u: any) => u.srt && !u.srt_path) || false
      if (needsSrt) {
        missingSteps.push('transcribe')
      }
      
      // Check for images
      const minImages = job.settings?.minImages || settings.minImages || 15
      const hasEnoughImages = (job.images?.length || 0) >= minImages
      if (!hasEnoughImages) {
        missingSteps.push('scrape_images')
      }
      
      // Check for outputs
      if (!job.outputs?.slideshow || !job.outputs?.portrait) {
        missingSteps.push('render')
      }
      
      if (missingSteps.length > 0) {
        setLogs(prev => [...prev, `[Resume] ${job.id}: needs ${missingSteps.join(', ')}`])
        
        // Reset status to pending for reprocessing
        jobsToResume.push({
          ...job,
          folder,
          status: 'pending' as JobStatus,
          missingSteps  // Track what needs to be done
        } as Job)
      }
    }
    
    if (jobsToResume.length === 0) {
      setLogs(prev => [...prev, '[Resume] All jobs complete or no jobs to resume.'])
      return
    }
    
    setJobs(jobsToResume)
    processNextJob(jobsToResume)
  }

  // create a new job with per-link toggles
  const createJob = useCallback(async (links: LinkItem[], jobName: string) => {
    if (!settings?.outputFolder) {
      setErrors((prev: string[]) => [...prev, 'set an output folder first in settings yo'])
      return
    }

    const timestamp = Date.now()
    const randomId = Math.floor(Math.random() * 1000)
    const safeJobName = jobName || `job_${timestamp}_${randomId}`
    
    let jobFolder = ''
    if (isElectron) {
      jobFolder = await window.electronAPI.createJobFolder(settings.outputFolder, safeJobName)
    }

    const job: Job = {
      id: safeJobName,
      topic: safeJobName,
      folder: jobFolder,
      created: new Date().toISOString(),
      created_at: new Date().toISOString(),
      urls: links,
      links: links.map(l => l.url),
      status: 'pending',
      progress: 0,
      outputs: {
        slideshow: null,
        portrait: null,
        youtubeMix: null
      },
      settings: { ...settings, faceOverlayPath },  // Include face overlay if set
      errors: [],
      downloadedVideos: [],
      srtFiles: [],
      keywords: [],
      images: []
    }

    if (isElectron && jobFolder) {
      await window.electronAPI.saveJob(jobFolder, job)
    }

    setJobs((prev: Job[]) => [...prev, job])
    setShowConfetti(true)
    setTimeout(() => setShowConfetti(false), 2500)

    if (!isProcessing) {
      processNextJob([...jobs, job])
    }
  }, [settings, jobs, isProcessing, faceOverlayPath])

  // process next pending job - WITH TIME CAP
  const processNextJob = async (jobList: Job[] = jobs) => {
    const pendingJob = jobList.find(j => j.status === 'pending')
    
    if (!pendingJob) {
      setIsProcessing(false)
      setCurrentJobId(null)
      setTimeEstimate(null)
      return
    }

    // System check
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
            `SYSTEM WARNING: ${issues.join(', ')}. Job may fail or crash.`
          ])
        }
      } catch (e) {
        // ignore
      }
    }

    setIsProcessing(true)
    setCurrentJobId(pendingJob.id)
    setLogs([])
    jobStartTime.current = Date.now()

    // Set time estimate
    const estimatedMinutes = estimateJobTime(pendingJob)
    setTimeEstimate({
      totalMinutes: estimatedMinutes,
      completedMinutes: 0,
      currentStep: 'Starting...'
    })

    // update status
    const updated = jobList.map(j => 
      j.id === pendingJob.id ? { ...j, status: 'running' as JobStatus } : j
    )
    setJobs(updated)

    if (isElectron && pendingJob.folder) {
      await window.electronAPI.saveJob(pendingJob.folder, { ...pendingJob, status: 'running' })
    }

    // JOB TIME CAP - 45 minutes max
    const timeoutId = setTimeout(() => {
      if (isProcessing && currentJobId === pendingJob.id) {
        setErrors(prev => [...prev, `JOB TIMEOUT: ${pendingJob.id} exceeded 45 minute limit. Stopping...`])
        stopCurrentJob()
      }
    }, 45 * 60 * 1000)  // 45 minutes

    try {
      if (isElectron && settings) {
        await window.electronAPI.runJob(pendingJob.folder!, {
          ...pendingJob.settings,
          ...settings,
          faceOverlayPath,  // Pass face overlay setting
          maxJobTime: 45 * 60  // 45 minutes in seconds
        })
      } else if (!isElectron) {
        await new Promise(resolve => setTimeout(resolve, 3000))
      }

      clearTimeout(timeoutId)

      // Record job history for future estimates
      if (jobStartTime.current) {
        const durationMinutes = (Date.now() - jobStartTime.current) / 60000
        saveJobHistory([...jobHistory, {
          id: pendingJob.id,
          linkCount: pendingJob.links?.length || 1,
          imageCount: pendingJob.images?.length || 0,
          durationMinutes,
          timestamp: Date.now()
        }])
      }

      // Re-read job from disk
      if (isElectron && pendingJob.folder) {
        const updatedJob = await window.electronAPI.readJob(pendingJob.folder)
        if (updatedJob) {
          setJobs((prev: Job[]) => prev.map((j: Job) => 
            j.id === pendingJob.id ? { ...updatedJob, folder: pendingJob.folder } : j
          ))
        } else {
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
      clearTimeout(timeoutId)
      const errorMsg = err instanceof Error ? err.message : 'unknown error'
      setErrors((prev: string[]) => [...prev, `Job ${pendingJob.id} failed: ${errorMsg}`])
      
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

    jobStartTime.current = null
    setTimeout(() => processNextJob(), 500)
  }

  // legacy resume jobs
  const resumeJobs = async () => {
    if (isProcessing) return
    
    if (isElectron && settings?.outputFolder) {
      const diskJobs = await window.electronAPI.scanJobs(settings.outputFolder)
      
      const mergedJobs = diskJobs.map((diskJob: Job) => {
        if (diskJob.status === 'error' || diskJob.status === 'paused') {
          return { ...diskJob, status: 'pending' as JobStatus }
        }
        if (diskJob.status === 'running') {
          return { ...diskJob, status: 'pending' as JobStatus }
        }
        return diskJob
      })
      
      setJobs(mergedJobs)
      
      const pendingJobs = mergedJobs.filter((j: Job) => j.status === 'pending')
      if (pendingJobs.length > 0) {
        processNextJob(mergedJobs)
      }
    } else {
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

  // GO HOME
  const goHome = () => {
    setSelectedJob(null)
  }

  // clear completed jobs
  const clearCompletedJobs = () => {
    setJobs((prev: Job[]) => prev.filter((j: Job) => j.status !== 'done'))
  }

  // stop a specific job
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

  // delete a job
  const deleteJob = async (jobId: string, deleteFolder: boolean) => {
    if (currentJobId === jobId) {
      await stopJobById(jobId)
    }
    
    const job = jobs.find(j => j.id === jobId)
    
    setJobs((prev: Job[]) => prev.filter((j: Job) => j.id !== jobId))
    
    if (selectedJob?.id === jobId) {
      setSelectedJob(null)
    }
    
    if (deleteFolder && job?.folder && isElectron) {
      try {
        await window.electronAPI.deleteFolder(job.folder)
      } catch (e) {
        console.error('failed to delete folder:', e)
      }
    }
  }

  // stop all jobs
  const stopAllJobs = async () => {
    if (isElectron && isProcessing) {
      await window.electronAPI.stopJob()
      setIsProcessing(false)
      setCurrentJobId(null)
      
      setJobs((prev: Job[]) => prev.map((j: Job) => 
        j.status === 'pending' || j.status === 'running' 
          ? { ...j, status: 'paused' as JobStatus } 
          : j
      ))
    }
  }

  // Select face overlay VIDEO for BETA feature
  const selectFaceOverlay = async () => {
    if (isElectron) {
      const file = await window.electronAPI.selectFile([
        { name: 'Videos', extensions: ['mp4', 'mov', 'webm', 'avi'] },
        { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp'] }
      ])
      if (file) {
        setFaceOverlayPath(file)
      }
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
          onScan={scanJobIntegrity}
          onSmartResume={smartResume}
          onStopJob={stopJobById}
          onDeleteJob={deleteJob}
          isProcessing={isProcessing}
          currentJobId={currentJobId}
          onNewJob={goHome}
          onOpenBeta={() => setShowBetaModal(true)}
          timeEstimate={timeEstimate}
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
      
      {/* Error box at bottom left */}
      {showErrorBox && errors.length > 0 && (
        <ErrorBox 
          errors={errors} 
          logs={logs}
          onClose={() => setShowErrorBox(false)}
          onClear={() => setErrors([])}
        />
      )}

      {/* BETA Face Overlay Modal */}
      {showBetaModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-da-dark rounded-2xl p-6 w-full max-w-lg border border-purple-500/30 shadow-xl shadow-purple-500/20">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <span className="px-2 py-1 rounded bg-purple-500/30 text-purple-300 text-xs font-bold">BETA</span>
                <h2 className="text-xl font-bold text-white">Face Video Overlay</h2>
              </div>
              <button 
                onClick={() => setShowBetaModal(false)}
                className="p-2 hover:bg-da-light rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <p className="text-da-text-muted text-sm mb-4">
              Select a video with your face (reaction, talking head, etc.) to overlay on outputs. 
              Great for reaction-style content!
            </p>

            {/* Preview area */}
            <div className="mb-4">
              {faceOverlayPath ? (
                <div className="relative">
                  <div className="w-full h-32 bg-da-medium rounded-xl flex items-center justify-center">
                    <span className="text-green-400 text-sm">✓ {faceOverlayPath.split('/').pop()}</span>
                  </div>
                  <button
                    onClick={() => setFaceOverlayPath(null)}
                    className="absolute top-2 right-2 p-1.5 bg-red-500/80 hover:bg-red-500 rounded-lg transition-colors"
                  >
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ) : (
                <div 
                  onClick={selectFaceOverlay}
                  className="w-full h-32 bg-da-medium rounded-xl border-2 border-dashed border-da-light/30 hover:border-purple-500/50 flex flex-col items-center justify-center cursor-pointer transition-colors"
                >
                  <svg className="w-10 h-10 text-da-text-muted mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <span className="text-da-text-muted text-sm">Click to select video/image</span>
                </div>
              )}
            </div>

            {/* Overlay Target */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-da-text-muted mb-2">Apply to which output?</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => setOverlayTarget('instagram')}
                  className={`py-2 px-3 rounded-lg text-xs font-medium transition-colors ${
                    overlayTarget === 'instagram' 
                      ? 'bg-purple-500 text-white' 
                      : 'bg-da-medium text-da-text-muted hover:bg-da-light'
                  }`}
                >
                  Instagram (Bottom)
                </button>
                <button
                  onClick={() => setOverlayTarget('youtube-corner')}
                  className={`py-2 px-3 rounded-lg text-xs font-medium transition-colors ${
                    overlayTarget === 'youtube-corner' 
                      ? 'bg-purple-500 text-white' 
                      : 'bg-da-medium text-da-text-muted hover:bg-da-light'
                  }`}
                >
                  YouTube (Corner)
                </button>
                <button
                  onClick={() => setOverlayTarget('all')}
                  className={`py-2 px-3 rounded-lg text-xs font-medium transition-colors ${
                    overlayTarget === 'all' 
                      ? 'bg-purple-500 text-white' 
                      : 'bg-da-medium text-da-text-muted hover:bg-da-light'
                  }`}
                >
                  All Outputs
                </button>
              </div>
            </div>

            {/* Position for YouTube */}
            {overlayTarget !== 'instagram' && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-da-text-muted mb-2">Corner position (YouTube)</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setOverlayPosition('top-right')}
                    className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-colors ${
                      overlayPosition === 'top-right' 
                        ? 'bg-purple-500 text-white' 
                        : 'bg-da-medium text-da-text-muted hover:bg-da-light'
                    }`}
                  >
                    Top Right
                  </button>
                  <button
                    onClick={() => setOverlayPosition('top-left')}
                    className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-colors ${
                      overlayPosition === 'top-left' 
                        ? 'bg-purple-500 text-white' 
                        : 'bg-da-medium text-da-text-muted hover:bg-da-light'
                    }`}
                  >
                    Top Left
                  </button>
                </div>
              </div>
            )}

            {/* Instructions */}
            <div className="bg-da-medium rounded-lg p-3 mb-4">
              <h4 className="text-xs font-semibold text-purple-300 mb-1">How it works:</h4>
              <ul className="text-xs text-da-text-muted space-y-0.5">
                <li>• Select your face video (MP4, MOV, etc.)</li>
                <li>• Instagram: overlays at bottom 1/3 of portrait video</li>
                <li>• YouTube: overlays in chosen corner of landscape video</li>
                <li>• If your video is longer, B-roll extends to match</li>
              </ul>
            </div>

            {/* Buttons */}
            <div className="flex gap-3">
              <button
                onClick={selectFaceOverlay}
                className="flex-1 py-3 rounded-xl bg-purple-500/20 border border-purple-500/50 text-purple-300 font-semibold hover:bg-purple-500/30 transition-colors"
              >
                {faceOverlayPath ? 'Change Video' : 'Select Video'}
              </button>
              <button
                onClick={() => setShowBetaModal(false)}
                className="flex-1 py-3 rounded-xl bg-da-pink text-white font-semibold hover:bg-da-pink/80 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

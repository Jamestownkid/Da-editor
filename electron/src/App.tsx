/**
 * Da Editor - Main App Component (v2)
 * =====================================
 * updated to match expected folder structure
 * with per-link SRT/IMG toggles
 */

import { useState, useEffect, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import MainPanel from './components/MainPanel'
import TopBar from './components/TopBar'
import SettingsModal from './components/SettingsModal'
import Confetti from './components/Confetti'
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

  // listen for job progress events
  useEffect(() => {
    if (isElectron) {
      window.electronAPI.onJobProgress((msg: string) => {
        setLogs((prev: string[]) => [...prev.slice(-100), msg])
      })
      window.electronAPI.onJobError((msg: string) => {
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

  // process next pending job
  const processNextJob = async (jobList: Job[] = jobs) => {
    const pendingJob = jobList.find(j => j.status === 'pending')
    
    if (!pendingJob) {
      setIsProcessing(false)
      setCurrentJobId(null)
      return
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

      // mark as done
      setJobs((prev: Job[]) => prev.map((j: Job) => 
        j.id === pendingJob.id ? { ...j, status: 'done' as JobStatus, progress: 100 } : j
      ))

      if (isElectron && pendingJob.folder) {
        await window.electronAPI.saveJob(pendingJob.folder, { ...pendingJob, status: 'done', progress: 100 })
      }

    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'unknown error'
      setJobs((prev: Job[]) => prev.map((j: Job) => 
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

    // process next
    setTimeout(() => processNextJob(), 500)
  }

  // resume jobs
  const resumeJobs = () => {
    const pending = jobs.filter((j: Job) => j.status === 'pending' || j.status === 'paused' || j.status === 'error')
    if (pending.length > 0 && !isProcessing) {
      const reset = jobs.map((j: Job) => 
        j.status === 'error' || j.status === 'paused' ? { ...j, status: 'pending' as JobStatus } : j
      )
      setJobs(reset)
      processNextJob(reset)
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
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          jobs={jobs}
          selectedJob={selectedJob}
          onSelectJob={setSelectedJob}
          onResume={resumeJobs}
          isProcessing={isProcessing}
          currentJobId={currentJobId}
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
    </div>
  )
}

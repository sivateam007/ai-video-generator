import { useState, useRef, useCallback } from 'react'
import './App.css'

type Step = 'idle' | 'parsing' | 'enriching' | 'rendering' | 'audio' | 'assembling' | 'completed' | 'error'

const STEP_LABELS: Record<string, string> = {
  parsing: 'Parsing HTML content...',
  enriching: 'Generating AI-powered slides & narration...',
  rendering: 'Rendering slide images...',
  audio: 'Creating voice narration...',
  assembling: 'Assembling final video...',
  completed: 'Video ready!',
}

const STEP_ORDER = ['parsing', 'enriching', 'rendering', 'audio', 'assembling']

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [step, setStep] = useState<Step>('idle')
  const [jobId, setJobId] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [currentStepIdx, setCurrentStepIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const reset = useCallback(() => {
    setFile(null)
    setStep('idle')
    setJobId(null)
    setProgress(0)
    setMessage('')
    setErrorMsg('')
    setCurrentStepIdx(0)
  }, [])

  const handleFile = useCallback((f: File) => {
    if (!f.name.endsWith('.html') && !f.name.endsWith('.htm')) {
      setErrorMsg('Please select an HTML file.')
      return
    }
    setFile(f)
    setErrorMsg('')
  }, [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }, [handleFile])

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const onDragLeave = useCallback(() => setDragOver(false), [])

  const upload = useCallback(async () => {
    if (!file) return
    setStep('parsing')
    setProgress(5)
    setCurrentStepIdx(0)

    const form = new FormData()
    form.append('file', file)

    try {
      const res = await fetch('/api/upload', { method: 'POST', body: form })
      if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed')
      const { job_id } = await res.json()
      setJobId(job_id)

      // Connect to SSE stream
      const evtSource = new EventSource(`/api/stream/${job_id}`)

      evtSource.addEventListener('status', (e: Event) => {
        const data = JSON.parse((e as MessageEvent).data)
        setMessage(data.message || '')
        if (data.step === 'parsed') { setProgress(10) }
        if (data.step === 'enriching') { setStep('enriching'); setCurrentStepIdx(1); setProgress(15) }
        if (data.step === 'enriched') { setProgress(20) }
        if (data.step === 'rendering') { setStep('rendering'); setCurrentStepIdx(2); setProgress(25) }
        if (data.step === 'audio') { setStep('audio'); setCurrentStepIdx(3); setProgress(55) }
        if (data.step === 'assembling') { setStep('assembling'); setCurrentStepIdx(4); setProgress(80) }
      })

      evtSource.addEventListener('progress', (e: Event) => {
        const data = JSON.parse((e as MessageEvent).data)
        if (data.item === 'slide') {
          const fraction = parseInt(data.name.replace('slide_', '')) / data.count
          setProgress(25 + fraction * 30)
        }
        if (data.item === 'audio') {
          const fraction = parseInt(data.name.replace('audio_slide_', '')) / data.count
          setProgress(55 + fraction * 25)
        }
        if (data.item === 'segment') {
          setProgress(85)
        }
      })

      evtSource.addEventListener('complete', () => {
        setStep('completed')
        setProgress(100)
        setCurrentStepIdx(5)
        evtSource.close()
      })

      evtSource.addEventListener('error', (e: Event) => {
        const data = JSON.parse((e as MessageEvent).data)
        setStep('error')
        setErrorMsg(data.message || 'An error occurred')
        evtSource.close()
      })

      evtSource.onerror = () => {
        // Check status if SSE fails
        fetch(`/api/status/${job_id}`).then(r => r.json()).then(j => {
          if (j.status === 'completed') {
            setStep('completed')
            setProgress(100)
          } else if (j.status === 'failed') {
            setStep('error')
            setErrorMsg(j.error || 'Unknown error')
          }
        }).catch(() => {
          setStep('error')
          setErrorMsg('Connection lost')
        })
        evtSource.close()
      }

    } catch (err: any) {
      setStep('error')
      setErrorMsg(err.message || 'Upload failed')
    }
  }, [file])

  return (
    <div className="app">
      <div className="header">
        <div className="logo">
          🖥️ <span>HTML to Video</span> 🎬
        </div>
        <div className="tagline">Upload any HTML tutorial — get a polished educational video</div>
        <div className="sub">JT Group of Institution ✨ Tamil Programming Education</div>
      </div>

      {step === 'idle' || step === 'error' ? (
        <div
          className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={() => inputRef.current?.click()}
        >
          {file ? (
            <div className="selected">
              <div className="file-name">{file.name}</div>
              <button className="upload-btn" onClick={(e) => { e.stopPropagation(); upload() }}>
                🚀 Generate Video
              </button>
            </div>
          ) : (
            <>
              <div className="icon">📄</div>
              <div className="text">Drop your HTML file here</div>
              <div className="hint">or click to browse &bull; .html or .htm</div>
            </>
          )}
          <input
            ref={inputRef}
            type="file"
            accept=".html,.htm"
            hidden
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
        </div>
      ) : null}

      {step === 'error' && (
        <div className="error-section">
          <div className="icon">❌</div>
          <div className="msg">{errorMsg}</div>
          <button className="new-btn" onClick={reset}>Upload another file</button>
        </div>
      )}

      {step !== 'idle' && step !== 'error' && (
        <div className="progress-section">
          <div className="status-text">
            {step === 'completed' ? '✅ ' : '⏳ '}
            {STEP_LABELS[step] || message}
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="steps">
            {STEP_ORDER.map((s, i) => {
              let cls = 'step'
              if (i < currentStepIdx) cls += ' done'
              else if (i === currentStepIdx) cls += ' active'
              return (
                <div key={s} className={cls}>
                  <div className="dot" />
                  <span>{STEP_LABELS[s]}</span>
                </div>
              )
            })}
            <div className={`step ${step === 'completed' ? 'done' : ''} ${step === 'completed' ? 'active' : ''}`}>
              <div className="dot" />
              <span>✅ Video ready for download!</span>
            </div>
          </div>
        </div>
      )}

      {step === 'completed' && (
        <div className="result-section">
          <div className="check">🎉</div>
          <div className="title">Your video is ready!</div>
          <div className="desc">Your educational video has been generated successfully.</div>
          <a className="download-btn" href={`/api/download/${jobId}`} download>
            ⬇️ Download MP4
          </a>
          <div style={{ marginTop: 16 }}>
            <button className="new-btn" onClick={reset}>Convert another file</button>
          </div>
        </div>
      )}

      <div className="footer">
        JT Group of Institution &bull; Tamil Programming Education
      </div>
    </div>
  )
}

export default App

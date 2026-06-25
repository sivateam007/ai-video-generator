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
      <header>
        <div className="header-container">
          <div className="logo">
            <div className="logo-icon">🎬</div>
            <h1>SK <span>AI Video Generator</span></h1>
          </div>
        </div>
      </header>

      <section className="hero">
        <div className="hero-content">
          <h2>Turn HTML Tutorials into Polished Videos</h2>
          <p>Upload any HTML document — AI extracts, structures, narrates, and generates a complete educational video</p>
        </div>
      </section>

      <div className="container">
        {step === 'idle' || step === 'error' ? (
          <div className="content-section upload-section" style={{ textAlign: 'center', padding: '3rem' }}>
            <h2 style={{ border: 'none', display: 'block', textAlign: 'center', marginBottom: '1.5rem', fontSize: '1.8rem' }}>
              Upload Your HTML File
            </h2>
            {step === 'error' && (
              <div className="tip-box" style={{ marginTop: 0, marginBottom: '1.5rem', textAlign: 'left' }}>
                <h4>❌ Error</h4>
                <p>{errorMsg}</p>
              </div>
            )}
            <div
              className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
              onDrop={onDrop}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onClick={() => inputRef.current?.click()}
            >
              {file ? (
                <div className="selected">
                  <div className="file-icon">📄</div>
                  <div className="file-name">{file.name}</div>
                  <p style={{ color: '#666', margin: '0.5rem 0 1rem' }}>Ready to generate your video</p>
                  <button className="platform-btn active upload-btn" onClick={(e) => { e.stopPropagation(); upload() }}>
                    🚀 Generate Video
                  </button>
                </div>
              ) : (
                <>
                  <div className="upload-icon">📤</div>
                  <div className="upload-text">Drop your HTML file here</div>
                  <div className="upload-hint">or click to browse &bull; .html or .htm</div>
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
          </div>
        ) : null}

        {step !== 'idle' && step !== 'error' && (
          <div className="content-section" style={{ padding: '2.5rem' }}>
            <h2 style={{ border: 'none', display: 'block', textAlign: 'center', marginBottom: '1.5rem' }}>
              {step === 'completed' ? '✅ ' : '⏳ '}
              {STEP_LABELS[step] || message}
            </h2>
            <div className="progress-bar-track">
              <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
            </div>
            <div className="steps" style={{ marginTop: '2rem' }}>
              {STEP_ORDER.map((s, i) => {
                let cls = 'step'
                if (i < currentStepIdx) cls += ' done'
                else if (i === currentStepIdx) cls += ' active'
                return (
                  <div key={s} className={cls}>
                    <span className="step-dot">{i < currentStepIdx ? '✓' : i === currentStepIdx ? '●' : '○'}</span>
                    <span>{STEP_LABELS[s]}</span>
                  </div>
                )
              })}
              <div className={`step ${step === 'completed' ? 'done active' : ''}`}>
                <span className="step-dot">{step === 'completed' ? '✓' : '○'}</span>
                <span>Video ready for download!</span>
              </div>
            </div>
          </div>
        )}

        {step === 'completed' && (
          <div className="content-section" style={{ textAlign: 'center', padding: '3rem' }}>
            <h2 style={{ border: 'none', display: 'block', textAlign: 'center', color: '#27ae60', fontSize: '2rem' }}>
              🎉 Your Video is Ready!
            </h2>
            <p style={{ fontSize: '1.2rem', color: '#555', margin: '1rem 0 2rem' }}>
              Your educational video has been generated successfully. Click below to download.
            </p>
            <div className="platform-buttons" style={{ justifyContent: 'center', marginBottom: '1.5rem' }}>
              <a className="platform-btn active download-btn" href={`/api/download/${jobId}`} download style={{ fontSize: '1.1rem', padding: '14px 40px' }}>
                ⬇️ Download MP4 Video
              </a>
            </div>
            <button className="new-btn" onClick={reset}>Convert another file</button>
          </div>
        )}
      </div>

      <footer>
        <div className="footer-content">
          <div className="footer-column">
            <h3>SK AI Video Generator</h3>
            <p style={{ color: '#ddd', lineHeight: '1.8' }}>
              Upload HTML tutorials and get polished educational videos with AI-generated slides, narrations, and professional formatting.
            </p>
          </div>
          <div className="footer-column">
            <h3>How It Works</h3>
            <ul>
              <li><a href="#">1. Upload your HTML file</a></li>
              <li><a href="#">2. AI extracts &amp; structures content</a></li>
              <li><a href="#">3. Slides are rendered</a></li>
              <li><a href="#">4. Voice narration is generated</a></li>
              <li><a href="#">5. Video is assembled &amp; ready</a></li>
            </ul>
          </div>
          <div className="footer-column">
            <h3>Contact</h3>
            <ul>
              <li><a href="#">GitHub</a></li>
              <li><a href="#">Documentation</a></li>
              <li><a href="#">Report Issue</a></li>
            </ul>
          </div>
        </div>
        <div className="copyright">
          &copy; 2026 SK AI Video Generator &bull; Turn HTML into Educational Videos
        </div>
      </footer>
    </div>
  )
}

export default App

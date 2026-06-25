"""FastAPI backend for HTML-to-Video application."""
import os, sys, json, uuid, asyncio, shutil
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from content_parser import parse_html
from ai_enricher import enrich_content
from slide_renderer import render_slides
from audio_gen import generate_audio
from video_asm import assemble_video

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
FRONTEND_DIR = BASE_DIR.parent / "frontend" / "dist"

jobs: dict[str, dict] = {}
event_queues: dict[str, list] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    yield

app = FastAPI(title="HTML to Video", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

def emit(job_id: str, event: str, data: dict):
    if job_id in event_queues:
        event_queues[job_id].append({"event": event, "data": json.dumps(data)})

async def process_video(job_id: str, html_content: str, filename: str):
    try:
        emit(job_id, "status", {"step": "parsing", "message": "Parsing HTML content..."})
        parsed = parse_html(html_content)
        emit(job_id, "status", {"step": "parsed", "sections": len(parsed.sections), "message": f"Found {len(parsed.sections)} sections"})

        emit(job_id, "status", {"step": "enriching", "message": "Generating slide content with AI..."})
        slides = enrich_content(parsed)
        emit(job_id, "status", {"step": "enriched", "count": len(slides), "message": f"Created {len(slides)} slides"})

        job_dir = OUTPUT_DIR / job_id
        slides_dir = str(job_dir / "slides")
        audio_dir = str(job_dir / "audio")

        emit(job_id, "status", {"step": "rendering", "message": "Rendering slide images..."})
        async def slide_progress(name):
            emit(job_id, "progress", {"item": "slide", "name": name, "count": len(slides)})
        await render_slides(slides, parsed.title, slides_dir, on_progress=slide_progress)

        emit(job_id, "status", {"step": "audio", "message": "Generating narration audio..."})
        async def audio_progress(name):
            emit(job_id, "progress", {"item": "audio", "name": name, "count": len(slides)})
        audio_files = await generate_audio(slides, audio_dir, on_progress=audio_progress)

        emit(job_id, "status", {"step": "assembling", "message": "Assembling final video..."})
        output_file = str(job_dir / f"{Path(filename).stem}.mp4")
        def asm_progress(name):
            emit(job_id, "progress", {"item": "segment", "name": name})
        assemble_video(slides_dir, audio_files, output_file, on_progress=asm_progress)

        jobs[job_id]["output"] = output_file
        jobs[job_id]["status"] = "completed"
        emit(job_id, "complete", {"message": "Video ready!"})

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        emit(job_id, "error", {"message": str(e)})

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(('.html', '.htm')):
        raise HTTPException(400, "Only HTML files are supported")

    content = await file.read()
    try:
        html_text = content.decode('utf-8')
    except UnicodeDecodeError:
        html_text = content.decode('latin-1')

    job_id = uuid.uuid4().hex[:12]
    jobs[job_id] = {"status": "processing", "filename": file.filename}
    event_queues[job_id] = []

    asyncio.create_task(process_video(job_id, html_text, file.filename))

    return {"job_id": job_id, "filename": file.filename}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "error": job.get("error"),
        "output": job.get("output") is not None
    }

@app.get("/api/stream/{job_id}")
async def stream_events(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    async def event_generator():
        queue = event_queues.get(job_id, [])
        # Send any queued events
        for ev in queue:
            yield ev
        # Poll for new events
        while jobs.get(job_id, {}).get("status") not in ("completed", "failed"):
            while event_queues.get(job_id, []):
                yield event_queues[job_id].pop(0)
            await asyncio.sleep(0.5)
        # Drain remaining
        while event_queues.get(job_id, []):
            yield event_queues[job_id].pop(0)

    return EventSourceResponse(event_generator())

@app.get("/api/download/{job_id}")
async def download_video(job_id: str):
    job = jobs.get(job_id)
    if not job or not job.get("output"):
        raise HTTPException(404, "Video not found")
    output = job["output"]
    if not os.path.exists(output):
        raise HTTPException(404, "File not found")
    return FileResponse(
        output,
        media_type="video/mp4",
        filename=os.path.basename(output)
    )

@app.get("/api/jobs")
async def list_jobs():
    return {jid: {"status": j.get("status"), "filename": j.get("filename")} for jid, j in jobs.items()}

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if not FRONTEND_DIR.exists():
        return HTMLResponse("<h1>Frontend not built</h1><p>Run: cd frontend && npm install && npm run build</p>")
    index = FRONTEND_DIR / "index.html"
    return HTMLResponse(index.read_text(encoding="utf-8"))

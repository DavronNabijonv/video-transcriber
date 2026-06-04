"""
Video Transcriber — FastAPI
============================
POST /transcribe
  Form fields (send one):
    url   : str        — public video URL (YouTube, Instagram, etc.)
    file  : UploadFile — video file (.mp4, .mov, .avi, …)
    model : str        — whisper model: tiny|base|small|medium|large (default: base)

  Response:
    { "text": "...", "download_url": "/download/{id}" }

GET /download/{file_id}  →  transcript.txt file download
"""

import asyncio
import os
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from core import download_url, extract_audio, transcribe

app = FastAPI(title="Video Transcriber API", version="1.0.0")

# Allow all origins for now; restrict to your frontend URL once deployed.
# e.g. allow_origins=["https://your-frontend.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

ALLOWED_MODELS = {"tiny", "base", "small", "medium", "large"}

# In-memory transcript store: file_id -> (text, created_at_timestamp)
_transcripts: dict[str, tuple[str, float]] = {}
TRANSCRIPT_TTL = 3600  # seconds — entries expire after 1 hour


@app.on_event("startup")
async def _start_cleanup_task():
    asyncio.create_task(_cleanup_loop())


async def _cleanup_loop():
    while True:
        await asyncio.sleep(300)  # run every 5 minutes
        cutoff = time.time() - TRANSCRIPT_TTL
        expired = [k for k, (_, ts) in _transcripts.items() if ts < cutoff]
        for k in expired:
            _transcripts.pop(k, None)


@app.post("/transcribe")
async def transcribe_endpoint(
    url: str = Form(None),
    file: UploadFile = File(None),
    model: str = Form("base"),
):
    has_url = bool(url and url.strip())
    has_file = file is not None and bool(file.filename)

    if not has_url and not has_file:
        raise HTTPException(400, "Send either 'url' or 'file'.")
    if has_url and has_file:
        raise HTTPException(400, "Send only one: 'url' or 'file'.")
    if model not in ALLOWED_MODELS:
        raise HTTPException(400, f"Invalid model. Choose: {sorted(ALLOWED_MODELS)}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            if has_url:
                audio_path = download_url(url.strip(), tmp_dir)
            else:
                ext = Path(file.filename).suffix or ".mp4"
                video_path = os.path.join(tmp_dir, f"input{ext}")
                with open(video_path, "wb") as f:
                    f.write(await file.read())
                audio_path = extract_audio(video_path, tmp_dir)

            text = transcribe(audio_path, model_size=model)

        except RuntimeError as exc:
            raise HTTPException(422, str(exc))
        except Exception as exc:
            raise HTTPException(500, f"Unexpected error: {exc}")

    file_id = str(uuid.uuid4())
    _transcripts[file_id] = (text, time.time())

    return {"text": text, "download_url": f"/download/{file_id}"}


@app.get("/download/{file_id}")
async def download_transcript(file_id: str):
    if not file_id.replace("-", "").isalnum():
        raise HTTPException(400, "Invalid file ID.")

    entry = _transcripts.get(file_id)
    if entry is None:
        raise HTTPException(404, "Transcript not found or expired.")

    text, _ = entry
    return Response(
        content=text.encode("utf-8"),
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="transcript.txt"'},
    )

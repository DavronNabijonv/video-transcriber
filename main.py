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
GET /                    →  web UI
"""

import os
import uuid
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core import download_url, extract_audio, transcribe

app = FastAPI(title="Video Transcriber API", version="1.0.0")

TRANSCRIPTS_DIR = Path("transcripts")
TRANSCRIPTS_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

ALLOWED_MODELS = {"tiny", "base", "small", "medium", "large"}


@app.get("/")
async def index():
    return FileResponse("static/index.html")


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
    (TRANSCRIPTS_DIR / f"{file_id}.txt").write_text(text, encoding="utf-8")

    return {"text": text, "download_url": f"/download/{file_id}"}


@app.get("/download/{file_id}")
async def download_transcript(file_id: str):
    if not file_id.replace("-", "").isalnum():
        raise HTTPException(400, "Invalid file ID.")

    txt_path = TRANSCRIPTS_DIR / f"{file_id}.txt"
    if not txt_path.exists():
        raise HTTPException(404, "Transcript not found or expired.")

    return FileResponse(str(txt_path), media_type="text/plain", filename="transcript.txt")

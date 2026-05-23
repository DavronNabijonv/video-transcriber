"""
Shared transcription logic — used by FastAPI (main.py) and the desktop app.
"""

import os
from pathlib import Path


def download_url(url: str, tmp_dir: str) -> str:
    """Download best-quality audio from a public video URL via yt-dlp."""
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp not installed. Run: pip install yt-dlp")

    audio_path = os.path.join(tmp_dir, "audio.mp3")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmp_dir, "audio.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # yt-dlp may write a different extension; find the actual output file
    if not os.path.exists(audio_path):
        for name in os.listdir(tmp_dir):
            if name.startswith("audio"):
                audio_path = os.path.join(tmp_dir, name)
                break

    if not os.path.exists(audio_path):
        raise RuntimeError("yt-dlp finished but produced no audio. Check the URL.")

    return audio_path


def extract_audio(video_path: str, tmp_dir: str) -> str:
    """Extract audio from a local video file using ffmpeg."""
    try:
        import ffmpeg
    except ImportError:
        raise RuntimeError("ffmpeg-python not installed. Run: pip install ffmpeg-python")

    audio_path = os.path.join(tmp_dir, "audio.mp3")
    try:
        (
            ffmpeg
            .input(video_path)
            .output(audio_path, acodec="mp3", audio_bitrate="192k")
            .overwrite_output()
            .run(quiet=True)
        )
    except Exception as exc:
        stderr = getattr(exc, "stderr", b"")
        msg = stderr.decode(errors="replace") if stderr else str(exc)
        raise RuntimeError(f"ffmpeg error: {msg}")

    return audio_path


def transcribe(audio_path: str, model_size: str = "base") -> str:
    """Transcribe an audio file with OpenAI Whisper. Auto-detects language."""
    try:
        import whisper
    except ImportError:
        raise RuntimeError("openai-whisper not installed. Run: pip install openai-whisper")

    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path, language=None, verbose=False)
    return result["text"].strip()

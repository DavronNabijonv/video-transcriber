"""
Instagram Video → Text Transcriber
===================================
Ishlatish:
  python video_to_text.py --url "https://www.instagram.com/reel/..."
  python video_to_text.py --file "video.mp4"
  python video_to_text.py --url "..." --output both
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path


def check_dependencies():
    """Kerakli kutubxonalar o'rnatilganligini tekshiradi."""
    missing = []
    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp")
    try:
        import whisper
    except ImportError:
        missing.append("openai-whisper")
    try:
        import ffmpeg
    except ImportError:
        missing.append("ffmpeg-python")

    if missing:
        print("❌ Quyidagi kutubxonalar o'rnatilmagan:")
        for pkg in missing:
            print(f"   pip install {pkg}")
        print("\nBarini birdan o'rnatish:")
        print("   pip install yt-dlp openai-whisper ffmpeg-python")
        sys.exit(1)


def download_instagram_video(url: str, output_dir: str) -> str:
    """Instagram URL dan video yuklab oladi, audio sifatida saqlaydi."""
    import yt_dlp

    print(f"⬇️  Instagram'dan yuklab olinmoqda: {url}")

    audio_path = os.path.join(output_dir, "audio.mp3")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "audio.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,
        "no_warnings": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if not os.path.exists(audio_path):
        # Ba'zan extension farq qilishi mumkin
        for f in os.listdir(output_dir):
            if f.startswith("audio"):
                audio_path = os.path.join(output_dir, f)
                break

    print(f"✅ Audio saqlandi: {audio_path}")
    return audio_path


def extract_audio_from_file(video_path: str, output_dir: str) -> str:
    """Lokal video fayldan audio ajratib oladi."""
    import ffmpeg

    print(f"🎵 Audiodan ajratilmoqda: {video_path}")

    audio_path = os.path.join(output_dir, "audio.mp3")

    try:
        (
            ffmpeg
            .input(video_path)
            .output(audio_path, acodec="mp3", audio_bitrate="192k")
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        print(f"❌ FFmpeg xatosi: {e.stderr.decode()}")
        sys.exit(1)

    print(f"✅ Audio ajratildi: {audio_path}")
    return audio_path


def transcribe_audio(audio_path: str, model_size: str = "base") -> str:
    """Whisper AI yordamida audiodan matn ajratadi."""
    import whisper

    print(f"🤖 Whisper modeli yuklanmoqda ({model_size})...")
    print("   (Birinchi marta uzoq vaqt olishi mumkin)")

    model = whisper.load_model(model_size)

    print("📝 Matn ajratilmoqda...")
    result = model.transcribe(audio_path, language="en", verbose=False)

    text = result["text"].strip()
    print(f"✅ Matn ajratildi! ({len(text)} belgi)")
    return text


def save_results(text: str, output_mode: str, base_name: str):
    """Natijani saqlaydi va/yoki ekranga chiqaradi."""

    if output_mode in ("screen", "both"):
        print("\n" + "=" * 60)
        print("📄 MATN NATIJASI:")
        print("=" * 60)
        print(text)
        print("=" * 60)

    if output_mode in ("file", "both"):
        txt_path = f"{base_name}_transcript.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\n💾 Fayl saqlandi: {txt_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Instagram video yoki lokal fayldan matn ajratish"
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", type=str, help="Instagram video URL manzili")
    source.add_argument("--file", type=str, help="Lokal video fayl yo'li (.mp4, .mov va b.)")

    parser.add_argument(
        "--output",
        choices=["screen", "file", "both"],
        default="both",
        help="Natijani qayerga chiqarish (default: both)",
    )
    parser.add_argument(
        "--model",
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
        help="Whisper model hajmi — kattaroq = aniqroq lekin sekin (default: base)",
    )

    args = parser.parse_args()

    # Kutubxonalarni tekshirish
    check_dependencies()

    with tempfile.TemporaryDirectory() as tmp_dir:

        # 1. Audio olish
        if args.url:
            audio_path = download_instagram_video(args.url, tmp_dir)
            base_name = "instagram_video"
        else:
            if not os.path.exists(args.file):
                print(f"❌ Fayl topilmadi: {args.file}")
                sys.exit(1)
            audio_path = extract_audio_from_file(args.file, tmp_dir)
            base_name = Path(args.file).stem

        # 2. Matn ajratish
        text = transcribe_audio(audio_path, model_size=args.model)

        # 3. Natijani saqlash
        save_results(text, args.output, base_name)

    print("\n✅ Tayyor!")


if __name__ == "__main__":
    main()

"""
Video Transcriber — Desktop App (CustomTkinter)
================================================
Run:  python desktop_app.py
Requires: pip install -r requirements-desktop.txt

The desktop app calls core.py directly — no server needed.
"""

import tempfile
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from core import download_url, extract_audio, transcribe

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Video Transcriber")
        self.geometry("720x640")
        self.resizable(True, True)
        self.minsize(580, 500)

        self._transcript: str = ""
        self._build()

    # ── UI construction ────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Title
        ctk.CTkLabel(
            self, text="Video Transcriber",
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, pady=(24, 4), padx=24, sticky="w")

        ctk.CTkLabel(
            self, text="Extract text from any video — paste a URL or upload a file.",
            text_color="gray", font=ctk.CTkFont(size=13)
        ).grid(row=1, column=0, pady=(0, 12), padx=24, sticky="w")

        # Tabs
        self.tab_view = ctk.CTkTabview(self, height=130)
        self.tab_view.grid(row=2, column=0, padx=24, sticky="ew")
        self.tab_view.add("URL")
        self.tab_view.add("File")

        # — URL tab —
        self.tab_view.tab("URL").grid_columnconfigure(0, weight=1)
        self.url_entry = ctk.CTkEntry(
            self.tab_view.tab("URL"),
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=40, font=ctk.CTkFont(size=13)
        )
        self.url_entry.grid(row=0, column=0, padx=12, pady=(16, 8), sticky="ew")

        # — File tab —
        self.tab_view.tab("File").grid_columnconfigure(0, weight=1)
        self._file_path = ctk.StringVar(value="")

        ctk.CTkButton(
            self.tab_view.tab("File"),
            text="Browse Video File…",
            command=self._browse_file, height=40
        ).grid(row=0, column=0, padx=12, pady=(16, 6), sticky="ew")

        self.file_label = ctk.CTkLabel(
            self.tab_view.tab("File"),
            textvariable=self._file_path,
            text_color="#4caf82", font=ctk.CTkFont(size=12),
            wraplength=500, justify="left"
        )
        self.file_label.grid(row=1, column=0, padx=12, sticky="w")

        # Options row
        opts_frame = ctk.CTkFrame(self, fg_color="transparent")
        opts_frame.grid(row=3, column=0, padx=24, pady=4, sticky="ew")
        opts_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(opts_frame, text="Whisper model:", text_color="gray").grid(
            row=0, column=0, padx=(0, 8))
        self._model = ctk.StringVar(value="base")
        ctk.CTkOptionMenu(
            opts_frame,
            values=["tiny", "base", "small", "medium", "large"],
            variable=self._model, width=160
        ).grid(row=0, column=1, sticky="w")

        # Transcribe button
        self.submit_btn = ctk.CTkButton(
            self, text="Transcribe",
            command=self._start, height=44,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.submit_btn.grid(row=4, column=0, padx=24, pady=10, sticky="ew")

        # Status label
        self.status_label = ctk.CTkLabel(
            self, text="", text_color="gray", font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=5, column=0, padx=24, sticky="w")

        # Result area
        self.result_box = ctk.CTkTextbox(
            self, state="disabled",
            font=ctk.CTkFont(size=13), wrap="word"
        )
        self.result_box.grid(row=6, column=0, padx=24, pady=(4, 6), sticky="nsew")
        self.grid_rowconfigure(6, weight=1)

        # Action buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=7, column=0, padx=24, pady=(0, 20), sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        self.save_btn = ctk.CTkButton(
            btn_row, text="Save as .txt",
            command=self._save_txt, state="disabled",
            fg_color="transparent", border_width=2, border_color="#6c63ff",
            text_color="#6c63ff", hover_color="#1a1d27"
        )
        self.save_btn.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.copy_btn = ctk.CTkButton(
            btn_row, text="Copy Text",
            command=self._copy_text, state="disabled",
            fg_color="transparent", border_width=2, border_color="gray",
            text_color="gray", hover_color="#22263a"
        )
        self.copy_btn.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    # ── Actions ────────────────────────────────────────────────────────────

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select a video file",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv *.webm *.m4v"),
                       ("All files", "*.*")]
        )
        if path:
            self._file_path.set(path)

    def _start(self):
        self.submit_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self.copy_btn.configure(state="disabled")
        self._set_result("")
        self._set_status("Working… this may take a few minutes.", "gray")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            active = self.tab_view.get()
            with tempfile.TemporaryDirectory() as tmp:
                if active == "URL":
                    url = self.url_entry.get().strip()
                    if not url:
                        raise ValueError("Please enter a URL first.")
                    audio = download_url(url, tmp)
                else:
                    path = self._file_path.get()
                    if not path:
                        raise ValueError("Please select a file first.")
                    audio = extract_audio(path, tmp)

                self._transcript = transcribe(audio, self._model.get())

            self.after(0, self._on_success)
        except Exception as exc:
            self.after(0, lambda: self._on_error(str(exc)))

    def _on_success(self):
        self._set_result(self._transcript)
        self._set_status(f"Done! {len(self._transcript)} characters.", "#4caf82")
        self.submit_btn.configure(state="normal")
        self.save_btn.configure(state="normal")
        self.copy_btn.configure(state="normal")

    def _on_error(self, msg: str):
        self._set_status(f"Error: {msg}", "#e05c5c")
        self.submit_btn.configure(state="normal")

    def _save_txt(self):
        if not self._transcript:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt")],
            initialfile="transcript.txt"
        )
        if path:
            Path(path).write_text(self._transcript, encoding="utf-8")
            self._set_status(f"Saved: {path}", "#4caf82")

    def _copy_text(self):
        self.clipboard_clear()
        self.clipboard_append(self._transcript)
        self.copy_btn.configure(text="Copied!")
        self.after(2000, lambda: self.copy_btn.configure(text="Copy Text"))

    # ── Helpers ────────────────────────────────────────────────────────────

    def _set_result(self, text: str):
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        if text:
            self.result_box.insert("1.0", text)
        self.result_box.configure(state="disabled")

    def _set_status(self, msg: str, color: str = "gray"):
        self.status_label.configure(text=msg, text_color=color)


if __name__ == "__main__":
    App().mainloop()

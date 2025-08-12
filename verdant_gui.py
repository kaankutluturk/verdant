#!/usr/bin/env python3
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from tkinter import StringVar

from verdant import (
    PresetsManager,
    UserPreferences,
    ModelDownloader,
    HardwareDetector,
    AIInference,
    get_capabilities,
)

APP_TITLE = "Verdant (Local AI)"

DARK = {
    "bg": "#0f1214",
    "panel": "#151a1e",
    "text": "#eaf2f6",
    "muted": "#9fb1bd",
    "brand": "#5bd174",
    "user_bubble": "#1d242a",
    "assistant_bubble": "#0f2b1a",
}
LIGHT = {
    "bg": "#ffffff",
    "panel": "#f4f7f9",
    "text": "#0f1214",
    "muted": "#51636f",
    "brand": "#2aa198",
    "user_bubble": "#e9eef2",
    "assistant_bubble": "#eaf6ee",
}

class VerdantGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("960x680")
        self.root.minsize(720, 540)

        # State
        self.presets = PresetsManager.load_presets()
        self.prefs_path = None
        self.prefs = UserPreferences.load(self.prefs_path)
        self.model_key = StringVar(value=self.prefs.get("model", "mistral-7b-q4"))
        self.threads_var = StringVar(value=str(self.prefs.get("threads") or ""))
        self.context_var = StringVar(value=str(self.prefs.get("context") or ""))
        self.temp_var = tk.DoubleVar(value=float(self.prefs.get("temperature", 0.7)))
        self.top_p_var = tk.DoubleVar(value=float(self.prefs.get("top_p", 0.9)))
        self.preset_var = StringVar(value="")
        self.status_var = StringVar(value="Ready")
        self.is_generating = False
        self.caps = get_capabilities()
        self.theme = DARK
        self.theme_mode = StringVar(value="dark")
        # progress
        self.download_progress = tk.DoubleVar(value=0.0)
        # chat structures
        self.chat_bubbles = []  # list of (frame, label, sender)
        self.current_assistant_label = None

        self._apply_theme()
        self._build_ui()

    def _apply_theme(self):
        colors = self.theme
        self.root.configure(bg=colors["bg"])
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=colors["bg"])
        style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
        style.configure("TButton", padding=6)
        style.map("TButton", foreground=[("disabled", colors["muted"])])
        style.configure("TProgressbar", troughcolor=colors["panel"], background=colors["brand"], darkcolor=colors["brand"], lightcolor=colors["brand"])

    def _build_ui(self):
        colors = self.theme
        self.root.rowconfigure(2, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Header
        header = ttk.Frame(self.root)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        title = ttk.Label(header, text="Verdant", font=("Segoe UI", 12, "bold"))
        title.pack(side="left")
        # status on right
        ttk.Label(header, textvariable=self.status_var, foreground=colors["muted"]).pack(side="right")
        # Theme and settings
        theme_cb = ttk.Combobox(header, values=["dark", "light"], textvariable=self.theme_mode, width=6, state="readonly")
        theme_cb.pack(side="right", padx=8)
        theme_cb.bind("<<ComboboxSelected>>", self._on_theme_change)
        ttk.Button(header, text="Settings", command=self._open_settings).pack(side="right")

        # Download progress bar (setup)
        self.setup_prog = ttk.Progressbar(self.root, maximum=100, variable=self.download_progress)
        self.setup_prog.grid(row=1, column=0, sticky="ew", padx=10)

        # Chat area (scrollable)
        chat_wrap = ttk.Frame(self.root)
        chat_wrap.grid(row=2, column=0, sticky="nsew", padx=10, pady=6)
        self.root.rowconfigure(2, weight=1)
        chat_canvas = tk.Canvas(chat_wrap, highlightthickness=0, bg=colors["bg"])
        chat_scroll = ttk.Scrollbar(chat_wrap, orient="vertical", command=chat_canvas.yview)
        self.chat_frame = ttk.Frame(chat_canvas)
        self.chat_frame.bind("<Configure>", lambda e: chat_canvas.configure(scrollregion=chat_canvas.bbox("all")))
        chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        chat_canvas.configure(yscrollcommand=chat_scroll.set)
        chat_canvas.pack(side="left", fill="both", expand=True)
        chat_scroll.pack(side="right", fill="y")

        # Input bar
        input_bar = ttk.Frame(self.root)
        input_bar.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        input_bar.columnconfigure(0, weight=1)
        self.input_text = tk.Text(input_bar, height=3, wrap="word")
        self._style_text_widget(self.input_text)
        self.input_text.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.input_text.bind("<Return>", self._on_enter)
        self.input_text.bind("<Shift-Return>", lambda e: self._insert_newline())
        ttk.Button(input_bar, text="Send", command=self.on_send).grid(row=0, column=1)

        # Initial hint
        self._add_system_note("Type your message and press Enter. Shift+Enter for new line.")

    def _style_text_widget(self, w: tk.Text):
        colors = self.theme
        w.configure(bg=colors["panel"], fg=colors["text"], insertbackground=colors["text"], highlightthickness=0, bd=0)

    def _on_theme_change(self, *_):
        self.theme = DARK if self.theme_mode.get() == "dark" else LIGHT
        self._apply_theme()
        # Re-style text widgets
        try:
            self._style_text_widget(self.input_text)
            for _, lbl, _ in self.chat_bubbles:
                # Labels inherit from style; rebuild bubble backgrounds on next messages
                lbl.configure(background=self.theme["assistant_bubble"])  # will be adjusted by sender when appended
        except Exception:
            pass

    def _add_bubble(self, text: str, sender: str):
        colors = self.theme
        row = ttk.Frame(self.chat_frame)
        row.pack(fill="x", pady=4)
        # alignment
        inner = ttk.Frame(row)
        if sender == "user":
            inner.pack(anchor="e", padx=4)
            bg = colors["user_bubble"]
        elif sender == "assistant":
            inner.pack(anchor="w", padx=4)
            bg = colors["assistant_bubble"]
        else:
            inner.pack(anchor="center", padx=4)
            bg = colors["panel"]
        # bubble label
        lbl = tk.Label(inner, text=text, wraplength=760, justify=("left" if sender != "user" else "left"),
                       bg=bg, fg=colors["text"], padx=10, pady=8, bd=0, highlightthickness=0)
        lbl.pack(side="left", fill="x")
        self.chat_bubbles.append((row, lbl, sender))
        # auto-scroll
        self.root.after(0, lambda: self.chat_frame.update_idletasks())

    def _add_system_note(self, text: str):
        self._add_bubble(text, sender="system")

    def on_send(self):
        if self.is_generating:
            return
        prompt = self.input_text.get("1.0", "end").strip()
        if not prompt:
            return
        self.input_text.delete("1.0", "end")
        self._add_bubble(prompt, sender="user")
        self._start_generation(prompt)

    def _on_enter(self, event):
        if event.state & 0x0001:  # Shift pressed
            return
        self.on_send()
        return "break"

    def _insert_newline(self):
        self.input_text.insert("insert", "\n")

    def _start_generation(self, prompt: str):
        self.status_var.set("Generating…")
        self.is_generating = True
        self._disable_send(True)
        # create an assistant bubble placeholder
        self._add_bubble("", sender="assistant")
        self.current_assistant_label = self.chat_bubbles[-1][1]
        self._run_generate_async(prompt)

    def _disable_send(self, busy: bool):
        # Disable send button
        for widget in self.root.winfo_children():
            try:
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button) and child.cget("text") == "Send":
                        child.configure(state=("disabled" if busy else "normal"))
            except Exception:
                continue

    def _open_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Settings")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.geometry("420x440")
        frame = ttk.Frame(dlg, padding=12)
        frame.pack(fill="both", expand=True)
        # Model
        ttk.Label(frame, text="Model").pack(anchor="w")
        model_box = ttk.Combobox(frame, textvariable=self.model_key, values=["mistral-7b-q4"], state="readonly")
        model_box.pack(fill="x", pady=(0, 8))
        # Threads/context
        ttk.Label(frame, text="Threads (blank = auto)").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.threads_var).pack(fill="x", pady=(0, 8))
        ttk.Label(frame, text=f"Context (max {get_capabilities()['max_context']})").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.context_var).pack(fill="x", pady=(0, 8))
        # Temp/top_p
        ttk.Label(frame, text=f"Temperature: {self.temp_var.get():.2f}").pack(anchor="w")
        temp_scale = ttk.Scale(frame, from_=0.0, to=1.5, orient="horizontal", variable=self.temp_var,
                               command=lambda v, l=frame.pack_slaves()[0]: None)
        temp_scale.pack(fill="x", pady=(0, 8))
        ttk.Label(frame, text=f"Top-p: {self.top_p_var.get():.2f}").pack(anchor="w")
        topp_scale = ttk.Scale(frame, from_=0.1, to=1.0, orient="horizontal", variable=self.top_p_var,
                               command=lambda v, l=frame.pack_slaves()[0]: None)
        topp_scale.pack(fill="x", pady=(0, 8))
        # Preset
        ttk.Label(frame, text="Preset (optional)").pack(anchor="w")
        preset_box = ttk.Combobox(frame, textvariable=self.preset_var, values=[""] + sorted(list(self.presets.keys())), state="readonly")
        preset_box.pack(fill="x", pady=(0, 12))
        # Actions
        btns = ttk.Frame(frame)
        btns.pack(fill="x")
        ttk.Button(btns, text="Save Prefs", command=self.on_save_prefs).pack(side="left")
        ttk.Button(btns, text="Load Prefs", command=self.on_load_prefs).pack(side="left", padx=8)
        ttk.Button(btns, text="Run Setup", command=self.on_setup).pack(side="right")

    def on_save_prefs(self):
        prefs = {
            "model": self.model_key.get() or "mistral-7b-q4",
            "threads": self._parse_int(self.threads_var.get()),
            "context": self._parse_int(self.context_var.get()),
            "temperature": float(self.temp_var.get()),
            "top_p": float(self.top_p_var.get()),
        }
        UserPreferences.save(prefs, self.prefs_path)
        self.status_var.set("Preferences saved")

    def on_load_prefs(self):
        self.prefs = UserPreferences.load(self.prefs_path)
        self.model_key.set(self.prefs.get("model", "mistral-7b-q4"))
        self.threads_var.set(str(self.prefs.get("threads") or ""))
        self.context_var.set(str(self.prefs.get("context") or ""))
        self.temp_var.set(float(self.prefs.get("temperature", 0.7)))
        self.top_p_var.set(float(self.prefs.get("top_p", 0.9)))
        self.status_var.set("Preferences loaded")

    def on_setup(self):
        if self.is_generating:
            return
        self.status_var.set("Setting up…")
        self.download_progress.set(0)
        self._disable_send(True)
        self.root.after(50, self._run_setup_async)

    def _run_setup_async(self):
        def task():
            try:
                model = self.model_key.get() or "mistral-7b-q4"
                if not HardwareDetector.check_requirements(model):
                    self._set_status("Requirements not met")
                    return
                dl = ModelDownloader()
                ok = dl.download_model(model, on_progress=self._on_download_progress)
                if not ok:
                    self._set_status("Download failed")
                    return
                if not dl.validate_model(model):
                    self._add_system_note("Model size/validation warning — continuing")
                self._set_status("Setup complete")
            except Exception as e:
                self._set_status(f"Setup error: {e}")
            finally:
                self._disable_send(False)
        threading.Thread(target=task, daemon=True).start()

    def _on_download_progress(self, percent: float, downloaded: int, total: int):
        try:
            self.root.after(0, lambda: self.download_progress.set(percent))
        except Exception:
            pass

    def _run_generate_async(self, prompt: str):
        def task():
            try:
                # Enforce context cap
                ctx = self._parse_int(self.context_var.get())
                if ctx and ctx > self.caps["max_context"]:
                    ctx = self.caps["max_context"]
                # Run inference
                model = self.model_key.get() or "mistral-7b-q4"
                dl = ModelDownloader()
                model_path = dl.get_model_path(model)
                if not model_path:
                    self._set_status("Model not found — run Setup first")
                    return
                # Preset
                final = prompt
                preset_name = self.preset_var.get().strip()
                if preset_name:
                    template = self.presets.get(preset_name)
                    if template:
                        final = f"{template}\n\nUser prompt: {prompt}"
                threads = self._parse_int(self.threads_var.get())
                temp = float(self.temp_var.get())
                top_p = float(self.top_p_var.get())
                ai = AIInference(model_path, n_ctx=ctx, n_threads=threads, temperature=temp, top_p=top_p)
                # Stream chunks when possible
                def append_chunk(txt: str):
                    if self.current_assistant_label:
                        current = self.current_assistant_label.cget("text")
                        self.current_assistant_label.configure(text=current + txt)
                for chunk in ai.generate_response_stream(final):
                    self.root.after(0, append_chunk, chunk)
                self._set_status("Done")
            except Exception as e:
                self._add_system_note(f"❌ Error: {e}")
                self._set_status("Error")
            finally:
                self.is_generating = False
                self._disable_send(False)
        threading.Thread(target=task, daemon=True).start()

    def _parse_int(self, s: str):
        try:
            v = int(s)
            return v if v > 0 else None
        except Exception:
            return None

    def _set_status(self, text: str):
        self.status_var.set(text)


def main():
    root = tk.Tk()
    VerdantGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main() 
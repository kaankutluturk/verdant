#!/usr/bin/env python3
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import StringVar
import tkinter.font as tkfont

from verdant import (
    PresetsManager,
    UserPreferences,
    ModelDownloader,
    HardwareDetector,
    AIInference,
    get_capabilities,
)

APP_TITLE = "Verdant (Local AI)"

PALETTE = {
    "dark": {
        "bg": "#0f1214",
        "panel": "#151a1e",
        "text": "#eaf2f6",
        "muted": "#9fb1bd",
        "brand": "#5BD174",
        "accent": "#2aa198",
        "user_bubble": "#1d242a",
        "assistant_bubble": "#0f2b1a",
        "badge_text": "#0b100d",
    },
    "light": {
        "bg": "#ffffff",
        "panel": "#f4f7f9",
        "text": "#0f1214",
        "muted": "#51636f",
        "brand": "#2aa198",
        "accent": "#5BD174",
        "user_bubble": "#e9eef2",
        "assistant_bubble": "#eaf6ee",
        "badge_text": "#0b100d",
    },
}

class VerdantGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("980x700")
        self.root.minsize(760, 560)

        # Fonts (slightly larger, modern feel)
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=10)
        tkfont.nametofont("TkTextFont").configure(size=10)

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
        self.theme_mode = StringVar(value="dark")
        self.colors = PALETTE[self.theme_mode.get()]
        # progress
        self.download_progress = tk.DoubleVar(value=0.0)
        # chat structures
        self.chat_bubbles = []
        self.current_assistant_label = None

        self._apply_theme()
        self._build_ui()

    def _apply_theme(self):
        c = self.colors
        self.root.configure(bg=c["bg"])
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=c["bg"]) 
        style.configure("TLabel", background=c["bg"], foreground=c["text"]) 
        style.configure("Muted.TLabel", background=c["bg"], foreground=c["muted"]) 
        # Accent button similar to website brand
        style.configure("Accent.TButton", background=c["brand"], foreground=c["badge_text"], padding=8)
        style.map("Accent.TButton",
                  background=[("active", c["accent"]), ("disabled", c["panel"])],
                  foreground=[("disabled", c["muted"])])
        style.configure("TButton", padding=6)
        style.configure("Card.TFrame", background=c["panel"], relief="flat")
        style.configure("Badge.TLabel", background=c["brand"], foreground=c["badge_text"], padding=4)
        style.configure("TProgressbar", troughcolor=c["panel"], background=c["brand"], darkcolor=c["brand"], lightcolor=c["brand"]) 

    def _build_ui(self):
        c = self.colors
        self.root.rowconfigure(3, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Header (brand + subtitle + theme + settings)
        header = ttk.Frame(self.root)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        brand_row = ttk.Frame(header)
        brand_row.pack(fill="x")
        ttk.Label(brand_row, text="Verdant", font=("Segoe UI", 13, "bold")).pack(side="left")
        ttk.Label(brand_row, text="Eco‑Conscious Local AI", style="Muted.TLabel").pack(side="left", padx=(10,0))
        # Theme and settings on right
        theme_cb = ttk.Combobox(brand_row, values=["dark", "light"], textvariable=self.theme_mode, width=6, state="readonly")
        theme_cb.pack(side="right")
        theme_cb.bind("<<ComboboxSelected>>", self._on_theme_change)
        ttk.Button(brand_row, text="Settings", command=self._open_settings).pack(side="right", padx=(0,8))

        # Badges row
        badges = ttk.Frame(header)
        badges.pack(fill="x", pady=(6,0))
        for text in ("Personal use • One‑time", "100% Local", "Privacy‑respecting"):
            lbl = ttk.Label(badges, text=text, style="Badge.TLabel")
            lbl.pack(side="left", padx=(0,8))

        # Setup progress bar
        self.setup_prog = ttk.Progressbar(self.root, maximum=100, variable=self.download_progress)
        self.setup_prog.grid(row=1, column=0, sticky="ew", padx=16)

        # Chat card
        chat_card = ttk.Frame(self.root, style="Card.TFrame")
        chat_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(10,6))
        ttk.Label(chat_card, textvariable=self.status_var, style="Muted.TLabel").pack(anchor="w", padx=10, pady=8)

        # Chat area (scrollable)
        chat_wrap = ttk.Frame(self.root)
        chat_wrap.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0,6))
        self.root.rowconfigure(3, weight=1)
        chat_canvas = tk.Canvas(chat_wrap, highlightthickness=0, bg=c["bg"])
        chat_scroll = ttk.Scrollbar(chat_wrap, orient="vertical", command=chat_canvas.yview)
        self.chat_frame = ttk.Frame(chat_canvas)
        self.chat_frame.bind("<Configure>", lambda e: chat_canvas.configure(scrollregion=chat_canvas.bbox("all")))
        chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        chat_canvas.configure(yscrollcommand=chat_scroll.set)
        chat_canvas.pack(side="left", fill="both", expand=True)
        chat_scroll.pack(side="right", fill="y")

        # Input bar
        input_bar = ttk.Frame(self.root)
        input_bar.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 14))
        input_bar.columnconfigure(0, weight=1)
        self.input_text = tk.Text(input_bar, height=3, wrap="word")
        self._style_text(self.input_text)
        self.input_text.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._attach_placeholder(self.input_text, "Write a message… (Enter to send, Shift+Enter = new line)")
        self.input_text.bind("<Return>", self._on_enter)
        self.input_text.bind("<Shift-Return>", lambda e: self._insert_newline())
        ttk.Button(input_bar, text="Send", style="Accent.TButton", command=self.on_send).grid(row=0, column=1)

        # Initial system note
        self._add_system_note("Welcome to Verdant — your eco‑conscious local AI. Run Settings → Run Setup to download the model.")

    def _style_text(self, w: tk.Text):
        c = self.colors
        w.configure(bg=c["panel"], fg=c["text"], insertbackground=c["text"], highlightthickness=0, bd=0, padx=8, pady=6)

    def _attach_placeholder(self, w: tk.Text, text: str):
        c = self.colors
        def on_focus_in(_):
            if w.get("1.0", "end").strip() == text:
                w.delete("1.0", "end")
                w.configure(fg=c["text"])
        def on_focus_out(_):
            if not w.get("1.0", "end").strip():
                w.insert("1.0", text)
                w.configure(fg=c["muted"])
        w.insert("1.0", text)
        w.configure(fg=c["muted"])
        w.bind("<FocusIn>", on_focus_in)
        w.bind("<FocusOut>", on_focus_out)

    def _on_theme_change(self, *_):
        self.colors = PALETTE[self.theme_mode.get()]
        self._apply_theme()
        try:
            self._style_text(self.input_text)
            # Update bubble backgrounds on next messages; keep existing as-is
        except Exception:
            pass

    def _add_bubble(self, text: str, sender: str):
        c = self.colors
        row = ttk.Frame(self.chat_frame)
        row.pack(fill="x", pady=4)
        inner = ttk.Frame(row)
        if sender == "user":
            inner.pack(anchor="e", padx=4)
            bg = c["user_bubble"]
        elif sender == "assistant":
            inner.pack(anchor="w", padx=4)
            bg = c["assistant_bubble"]
        else:
            inner.pack(anchor="center", padx=4)
            bg = c["panel"]
        lbl = tk.Label(inner, text=text, wraplength=800, justify="left",
                       bg=bg, fg=c["text"], padx=12, pady=10, bd=0, highlightthickness=0)
        lbl.pack(side="left", fill="x")
        self.chat_bubbles.append((row, lbl, sender))

    def _add_system_note(self, text: str):
        self._add_bubble(text, sender="system")

    def on_send(self):
        if self.is_generating:
            return
        prompt = self.input_text.get("1.0", "end").strip()
        if not prompt or prompt.startswith("Write a message…"):
            return
        self.input_text.delete("1.0", "end")
        self._add_bubble(prompt, sender="user")
        self._start_generation(prompt)

    def _on_enter(self, event):
        if event.state & 0x0001:
            return
        self.on_send()
        return "break"

    def _insert_newline(self):
        self.input_text.insert("insert", "\n")

    def _start_generation(self, prompt: str):
        self.status_var.set("Generating…")
        self.is_generating = True
        self._disable_send(True)
        self._add_bubble("", sender="assistant")
        self.current_assistant_label = self.chat_bubbles[-1][1]
        self._run_setup_if_needed_then_generate(prompt)

    def _disable_send(self, busy: bool):
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
        dlg.geometry("460x500")
        frame = ttk.Frame(dlg, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Model").pack(anchor="w")
        ttk.Combobox(frame, textvariable=self.model_key, values=["mistral-7b-q4"], state="readonly").pack(fill="x", pady=(0, 8))
        ttk.Label(frame, text="Threads (blank = auto)").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.threads_var).pack(fill="x", pady=(0, 8))
        ttk.Label(frame, text=f"Context (max {self.caps['max_context']})").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.context_var).pack(fill="x", pady=(0, 8))
        ttk.Label(frame, text=f"Temperature: {self.temp_var.get():.2f}").pack(anchor="w")
        ttk.Scale(frame, from_=0.0, to=1.5, orient="horizontal", variable=self.temp_var).pack(fill="x", pady=(0, 8))
        ttk.Label(frame, text=f"Top-p: {self.top_p_var.get():.2f}").pack(anchor="w")
        ttk.Scale(frame, from_=0.1, to=1.0, orient="horizontal", variable=self.top_p_var).pack(fill="x", pady=(0, 8))
        ttk.Label(frame, text="Preset (optional)").pack(anchor="w")
        ttk.Combobox(frame, textvariable=self.preset_var, values=[""] + sorted(list(self.presets.keys())), state="readonly").pack(fill="x", pady=(0, 12))
        btns = ttk.Frame(frame)
        btns.pack(fill="x")
        ttk.Button(btns, text="Save Prefs", command=self.on_save_prefs).pack(side="left")
        ttk.Button(btns, text="Load Prefs", command=self.on_load_prefs).pack(side="left", padx=8)
        ttk.Button(btns, text="Run Setup", style="Accent.TButton", command=self.on_setup).pack(side="right")

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

    def _run_setup_if_needed_then_generate(self, prompt: str):
        # Ensure model exists; if not, run setup then generate
        def after_setup():
            self._run_generate_async(prompt)
        def task():
            model = self.model_key.get() or "mistral-7b-q4"
            dl = ModelDownloader()
            if dl.get_model_path(model):
                self.root.after(0, self._run_generate_async, prompt)
                return
            try:
                if not HardwareDetector.check_requirements(model):
                    self._set_status("Requirements not met")
                    self._disable_send(False)
                    return
                ok = dl.download_model(model, on_progress=self._on_download_progress)
                if not ok:
                    self._set_status("Download failed")
                    self._disable_send(False)
                    return
                dl.validate_model(model)
                self.root.after(0, after_setup)
            except Exception as e:
                self._set_status(f"Setup error: {e}")
                self._disable_send(False)
        threading.Thread(target=task, daemon=True).start()

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
                dl.validate_model(model)
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
                # Model
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
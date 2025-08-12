#!/usr/bin/env python3
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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

APP_TITLE = "Verdant GUI (Experimental)"

DARK = {
    "bg": "#0f1214",
    "panel": "#151a1e",
    "text": "#eaf2f6",
    "muted": "#9fb1bd",
    "brand": "#5bd174",
}
LIGHT = {
    "bg": "#ffffff",
    "panel": "#f4f7f9",
    "text": "#0f1214",
    "muted": "#51636f",
    "brand": "#2aa198",
}

class VerdantGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("900x600")

        # State
        self.presets = PresetsManager.load_presets()
        self.prefs_path = None
        self.prefs = UserPreferences.load(self.prefs_path)
        self.model_key = tk.StringVar(value=self.prefs.get("model", "mistral-7b-q4"))
        self.threads_var = tk.StringVar(value=str(self.prefs.get("threads") or ""))
        self.context_var = tk.StringVar(value=str(self.prefs.get("context") or ""))
        self.temp_var = tk.DoubleVar(value=float(self.prefs.get("temperature", 0.7)))
        self.top_p_var = tk.DoubleVar(value=float(self.prefs.get("top_p", 0.9)))
        self.preset_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready")
        self.is_generating = False
        self.caps = get_capabilities()
        self.theme = DARK
        self.theme_mode = StringVar(value="dark")
        # progress and log
        self.download_progress = tk.DoubleVar(value=0.0)
        self.gen_progress = tk.DoubleVar(value=0.0)
        self.log_lines: list[str] = []

        self._build_ui()

    def _apply_theme(self):
        colors = self.theme
        self.root.configure(bg=colors["bg"])
        style = ttk.Style(self.root)
        # Use clam theme for better ttk styling consistency
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=colors["bg"])
        style.configure("TLabelframe", background=colors["bg"], foreground=colors["text"])
        style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
        style.configure("TButton", padding=6)
        style.map("TButton", foreground=[("disabled", colors["muted"])])
        style.configure("TProgressbar", troughcolor=colors["panel"], background=colors["brand"], darkcolor=colors["brand"], lightcolor=colors["brand"])
        # Text widgets
        def style_text_widget(w: tk.Text):
            w.configure(bg=colors["panel"], fg=colors["text"], insertbackground=colors["text"], highlightthickness=0, bd=0)
        # Apply to existing text areas if created
        try:
            style_text_widget(self.prompt_text)
            style_text_widget(self.response_text)
            style_text_widget(self.log_text)
        except Exception:
            pass

    def _build_ui(self):
        self._apply_theme()
        # Root layout: left settings, right chat
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        settings = ttk.Frame(self.root, padding=10)
        settings.grid(row=0, column=0, sticky="ns")

        main = ttk.Frame(self.root, padding=(0, 10, 10, 10))
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(2, weight=1)
        main.columnconfigure(0, weight=1)

        # Top bar with theme toggle
        topbar = ttk.Frame(self.root)
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(topbar, text="Theme:").pack(side="right")
        theme_cb = ttk.Combobox(topbar, values=["dark", "light"], textvariable=self.theme_mode, width=6, state="readonly")
        theme_cb.pack(side="right", padx=6, pady=6)
        theme_cb.bind("<<ComboboxSelected>>", self._on_theme_change)

        # Settings panel
        ttk.Label(settings, text="Model").grid(row=0, column=0, sticky="w")
        model_box = ttk.Combobox(settings, textvariable=self.model_key, state="readonly", width=20)
        model_box["values"] = ["mistral-7b-q4"]
        model_box.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(settings, text="Threads (blank = auto)").grid(row=2, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.threads_var, width=20).grid(row=3, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(settings, text="Context (blank = auto)").grid(row=4, column=0, sticky="w")
        ctx_entry = ttk.Entry(settings, textvariable=self.context_var, width=20)
        ctx_entry.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        if self.caps["max_context"] < 4096:
            ctx_entry.configure(state="normal")
            # Show hint under context
            ttk.Label(settings, text=f"Max {self.caps['max_context']} (Premium for more)", foreground="#9fb1bd").grid(row=6, column=0, sticky="w")
            temp_row = 7
        else:
            temp_row = 6

        ttk.Label(settings, text=f"Temperature: {self.temp_var.get():.2f}").grid(row=temp_row, column=0, sticky="w")
        temp_scale = ttk.Scale(settings, from_=0.0, to=1.5, orient="horizontal", variable=self.temp_var,
                               command=lambda v, lbl=settings.grid_slaves(row=temp_row, column=0)[0]: lbl.config(text=f"Temperature: {float(v):.2f}"))
        temp_scale.grid(row=temp_row+1, column=0, sticky="ew", pady=(0, 8))

        gpu_row = temp_row + 2
        gpu_label = ttk.Label(settings, text="GPU (Premium)")
        gpu_label.grid(row=gpu_row, column=0, sticky="w")
        gpu_toggle = ttk.Checkbutton(settings, state=("disabled" if not self.caps["allow_gpu"] else "normal"))
        gpu_toggle.grid(row=gpu_row+1, column=0, sticky="w", pady=(0,8))

        preset_row = gpu_row + 2
        ttk.Label(settings, text="Preset (optional)").grid(row=preset_row, column=0, sticky="w")
        preset_box = ttk.Combobox(settings, textvariable=self.preset_var, state="readonly", width=20)
        preset_box["values"] = [""] + sorted(list(self.presets.keys()))
        preset_box.grid(row=preset_row+1, column=0, sticky="ew", pady=(0, 8))

        btn_row = preset_row + 2
        ttk.Button(settings, text="Save Prefs", command=self.on_save_prefs).grid(row=btn_row, column=0, sticky="ew", pady=(4, 4))
        ttk.Button(settings, text="Load Prefs", command=self.on_load_prefs).grid(row=btn_row+1, column=0, sticky="ew")

        sep_row = btn_row + 2
        ttk.Separator(settings, orient="horizontal").grid(row=sep_row, column=0, sticky="ew", pady=8)
        ttk.Button(settings, text="Run Setup", command=self.on_setup).grid(row=sep_row+1, column=0, sticky="ew")

        # Main panel
        title = ttk.Frame(main)
        title.grid(row=0, column=0, sticky="ew")
        ttk.Label(title, text="Verdant Premium (Local)", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Label(title, textvariable=self.status_var, foreground="#5bd174").pack(side="right")

        prompt_label = ttk.Label(main, text="Prompt")
        prompt_label.grid(row=1, column=0, sticky="w")
        self.prompt_text = tk.Text(main, height=6, wrap="word")
        self.prompt_text.grid(row=2, column=0, sticky="nsew")

        buttons = ttk.Frame(main)
        buttons.grid(row=3, column=0, sticky="ew", pady=8)
        ttk.Button(buttons, text="Generate", command=self.on_generate).pack(side="left")
        ttk.Button(buttons, text="Clear", command=self.on_clear).pack(side="left", padx=(8, 0))

        ttk.Label(main, text="Response").grid(row=4, column=0, sticky="w")
        self.response_text = tk.Text(main, height=12, wrap="word")
        self.response_text.grid(row=5, column=0, sticky="nsew")

        # Inject progress bars
        self.setup_prog = ttk.Progressbar(self.root, maximum=100, variable=self.download_progress)
        self.setup_prog.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10)
        self.gen_prog = ttk.Progressbar(self.root, maximum=100, variable=self.gen_progress, mode="determinate")
        self.gen_prog.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10)

        # Simple log area
        log_frame = ttk.Frame(self.root)
        log_frame.grid(row=4, column=0, columnspan=2, sticky="nsew")
        self.root.rowconfigure(4, weight=1)
        self.log_text = tk.Text(log_frame, height=6, wrap="word")
        self.log_text.pack(fill="both", expand=True)

        # Footer info
        sysinfo = HardwareDetector.get_system_info()
        tier = HardwareDetector.get_performance_tier()
        ttk.Label(main, text=f"System: {sysinfo['platform']} • {sysinfo['cpu_count']} cores • {sysinfo['memory_gb']:.1f} GB RAM • Tier: {tier}", foreground="#9fb1bd").grid(row=6, column=0, sticky="w", pady=(8, 0))

    # Handlers
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
        self._disable_all(True)
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
                    self._append_log("Model size/validation warning — continuing")
                self._set_status("Setup complete")
            except Exception as e:
                self._set_status(f"Setup error: {e}")
            finally:
                self._disable_all(False)
        threading.Thread(target=task, daemon=True).start()

    def _on_download_progress(self, percent: float, downloaded: int, total: int):
        try:
            self.root.after(0, lambda: self.download_progress.set(percent))
        except Exception:
            pass

    def on_generate(self):
        if self.is_generating:
            return
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not prompt:
            messagebox.showinfo(APP_TITLE, "Please enter a prompt.")
            return
        self.response_text.delete("1.0", "end")
        self.status_var.set("Generating…")
        self.gen_progress.set(5)
        self.is_generating = True
        self._disable_all(True)
        self.root.after(50, self._run_generate_async, prompt)

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
                    self.response_text.insert("end", txt)
                    self.response_text.see("end")
                for chunk in ai.generate_response_stream(final):
                    self.root.after(0, append_chunk, chunk)
                    self.root.after(0, lambda: self.gen_progress.set(min(99, self.gen_progress.get() + 1)))
                self._set_status("Done")
            except Exception as e:
                self._append_response(f"❌ Error: {e}")
                self._set_status("Error")
            finally:
                self.is_generating = False
                self._disable_all(False)
                self.root.after(0, lambda: self.gen_progress.set(0))
        threading.Thread(target=task, daemon=True).start()

    def on_clear(self):
        self.prompt_text.delete("1.0", "end")
        self.response_text.delete("1.0", "end")
        self.status_var.set("Cleared")

    # Helpers
    def _parse_int(self, s: str):
        try:
            v = int(s)
            return v if v > 0 else None
        except Exception:
            return None

    def _append_response(self, text: str):
        self.response_text.insert("end", text + "\n")
        self.response_text.see("end")

    def _set_status(self, text: str):
        self.status_var.set(text)

    def _on_theme_change(self, *_):
        self.theme = DARK if self.theme_mode.get() == "dark" else LIGHT
        self._apply_theme()

    def _append_log(self, line: str):
        self.log_lines.append(line)
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")

    def _disable_all(self, busy: bool):
        # Minimal: disable generate/setup buttons while busy
        # For brevity we search by text; in a larger app, track references
        for widget in self.root.winfo_children():
            try:
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Button) and child.cget("text") in ("Generate", "Run Setup"):
                            child.configure(state=("disabled" if busy else "normal"))
            except Exception:
                continue


def main():
    root = tk.Tk()
    VerdantGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from verdant import (
    PresetsManager,
    UserPreferences,
    ModelDownloader,
    HardwareDetector,
    AIInference,
)

APP_TITLE = "Verdant GUI (Experimental)"

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

        self._build_ui()

    def _build_ui(self):
        # Root layout: left settings, right chat
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        settings = ttk.Frame(self.root, padding=10)
        settings.grid(row=0, column=0, sticky="ns")

        main = ttk.Frame(self.root, padding=(0, 10, 10, 10))
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(2, weight=1)
        main.columnconfigure(0, weight=1)

        # Settings panel
        ttk.Label(settings, text="Model").grid(row=0, column=0, sticky="w")
        model_box = ttk.Combobox(settings, textvariable=self.model_key, state="readonly", width=20)
        model_box["values"] = ["mistral-7b-q4"]
        model_box.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(settings, text="Threads (blank = auto)").grid(row=2, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.threads_var, width=20).grid(row=3, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(settings, text="Context (blank = auto)").grid(row=4, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.context_var, width=20).grid(row=5, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(settings, text=f"Temperature: {self.temp_var.get():.2f}").grid(row=6, column=0, sticky="w")
        temp_scale = ttk.Scale(settings, from_=0.0, to=1.5, orient="horizontal", variable=self.temp_var,
                               command=lambda v, lbl=settings.grid_slaves(row=6, column=0)[0]: lbl.config(text=f"Temperature: {float(v):.2f}"))
        temp_scale.grid(row=7, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(settings, text=f"Top-p: {self.top_p_var.get():.2f}").grid(row=8, column=0, sticky="w")
        topp_scale = ttk.Scale(settings, from_=0.1, to=1.0, orient="horizontal", variable=self.top_p_var,
                               command=lambda v, lbl=settings.grid_slaves(row=8, column=0)[0]: lbl.config(text=f"Top-p: {float(v):.2f}"))
        topp_scale.grid(row=9, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(settings, text="Preset (optional)").grid(row=10, column=0, sticky="w")
        preset_box = ttk.Combobox(settings, textvariable=self.preset_var, state="readonly", width=20)
        preset_box["values"] = [""] + sorted(list(self.presets.keys()))
        preset_box.grid(row=11, column=0, sticky="ew", pady=(0, 8))

        ttk.Button(settings, text="Save Prefs", command=self.on_save_prefs).grid(row=12, column=0, sticky="ew", pady=(4, 4))
        ttk.Button(settings, text="Load Prefs", command=self.on_load_prefs).grid(row=13, column=0, sticky="ew")

        ttk.Separator(settings, orient="horizontal").grid(row=14, column=0, sticky="ew", pady=8)
        ttk.Button(settings, text="Run Setup", command=self.on_setup).grid(row=15, column=0, sticky="ew")

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
        self.root.after(50, self._run_setup_async)

    def _run_setup_async(self):
        def task():
            try:
                model = self.model_key.get() or "mistral-7b-q4"
                if not HardwareDetector.check_requirements(model):
                    self._set_status("Requirements not met")
                    return
                dl = ModelDownloader()
                if not dl.download_model(model):
                    self._set_status("Download failed")
                    return
                if not dl.validate_model(model):
                    self._set_status("Validation failed")
                    return
                self._set_status("Setup complete")
            except Exception as e:
                self._set_status(f"Setup error: {e}")
        threading.Thread(target=task, daemon=True).start()

    def on_generate(self):
        if self.is_generating:
            return
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not prompt:
            messagebox.showinfo(APP_TITLE, "Please enter a prompt.")
            return
        self.response_text.delete("1.0", "end")
        self.status_var.set("Generating…")
        self.is_generating = True
        self.root.after(50, self._run_generate_async, prompt)

    def _run_generate_async(self, prompt: str):
        def task():
            try:
                # Find model
                model = self.model_key.get() or "mistral-7b-q4"
                dl = ModelDownloader()
                model_path = dl.get_model_path(model)
                if not model_path:
                    self._set_status("Model not found — run Setup first")
                    return
                # Build final prompt with preset
                final = prompt
                preset_name = self.preset_var.get().strip()
                if preset_name:
                    template = self.presets.get(preset_name)
                    if template:
                        final = f"{template}\n\nUser prompt: {prompt}"
                # Overrides
                threads = self._parse_int(self.threads_var.get())
                context = self._parse_int(self.context_var.get())
                temp = float(self.temp_var.get())
                top_p = float(self.top_p_var.get())
                # Run inference
                ai = AIInference(model_path, n_ctx=context, n_threads=threads, temperature=temp, top_p=top_p)
                out = ai.generate_response(final)
                self._append_response(out)
                self._set_status("Done")
            except Exception as e:
                self._append_response(f"❌ Error: {e}")
                self._set_status("Error")
            finally:
                self.is_generating = False
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


def main():
    root = tk.Tk()
    VerdantGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main() 
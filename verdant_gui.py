#!/usr/bin/env python3
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import StringVar
import tkinter.font as tkfont
import sys
import platform
import ctypes

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
        self.chat_canvas = None
        self._typing_job = None
        self._tooltips = []

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
        style.configure("AccentHover.TButton", background=c["accent"], foreground=c["badge_text"], padding=8)
        style.configure("TButton", padding=6)
        style.configure("Card.TFrame", background=c["panel"], relief="flat")
        style.configure("Badge.TLabel", background=c["brand"], foreground=c["badge_text"], padding=4)
        style.configure("TProgressbar", troughcolor=c["panel"], background=c["brand"], darkcolor=c["brand"], lightcolor=c["brand"]) 

        # Try to set dark titlebar on Windows
        self._apply_titlebar_dark(self.theme_mode.get() == "dark")

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

        # Header divider
        ttk.Separator(self.root, orient="horizontal").grid(row=1, column=0, sticky="ew", padx=16, pady=(4,0))

        # Setup progress bar
        self.setup_prog = ttk.Progressbar(self.root, maximum=100, variable=self.download_progress)
        self.setup_prog.grid(row=2, column=0, sticky="ew", padx=16)

        # Chat card
        chat_card = ttk.Frame(self.root, style="Card.TFrame")
        chat_card.grid(row=3, column=0, sticky="ew", padx=16, pady=(10,6))
        ttk.Label(chat_card, textvariable=self.status_var, style="Muted.TLabel").pack(anchor="w", padx=10, pady=8)

        # Chat area (scrollable)
        chat_wrap = ttk.Frame(self.root)
        chat_wrap.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0,6))
        self.root.rowconfigure(4, weight=1)
        self.chat_canvas = tk.Canvas(chat_wrap, highlightthickness=0, bg=c["bg"])
        chat_scroll = ttk.Scrollbar(chat_wrap, orient="vertical", command=self.chat_canvas.yview)
        self.chat_frame = ttk.Frame(self.chat_canvas)
        self.chat_frame.bind("<Configure>", lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))
        self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        self.chat_canvas.configure(yscrollcommand=chat_scroll.set)
        self.chat_canvas.pack(side="left", fill="both", expand=True)
        chat_scroll.pack(side="right", fill="y")

        # Input bar
        input_bar = ttk.Frame(self.root)
        input_bar.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 14))
        input_bar.columnconfigure(0, weight=1)
        self.input_text = tk.Text(input_bar, height=3, wrap="word")
        self._style_text(self.input_text)
        self.input_text.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._attach_placeholder(self.input_text, "Write a message… (Enter/Ctrl+Enter to send, Shift+Enter = new line)")
        self.input_text.bind("<Return>", self._on_enter)
        # Support Ctrl+Enter as send too
        self.input_text.bind("<Control-Return>", self._on_ctrl_enter)
        self.input_text.bind("<Shift-Return>", lambda e: self._insert_newline())
        send_btn = ttk.Button(input_bar, text="Send", style="Accent.TButton", command=self.on_send)
        send_btn.grid(row=0, column=1)
        self._add_tooltip(send_btn, "Send (Enter/Ctrl+Enter)")

        # Initial system note
        self._add_system_note("Welcome to Verdant — your eco‑conscious local AI. Run Settings → Run Setup to download the model.")
        # New chat button in header row (right under badges)
        actions = ttk.Frame(header)
        actions.pack(fill="x", pady=(6,0))
        new_btn = ttk.Button(actions, text="New chat", command=self._new_chat)
        new_btn.pack(side="left")
        self._add_tooltip(new_btn, "Start a new conversation")

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

    def _apply_titlebar_dark(self, enable: bool):
        # Windows dark titlebar via DWM API
        if platform.system() != "Windows":
            return
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # 19 on older builds; we try both
            val = ctypes.c_int(1 if enable else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(val), ctypes.sizeof(val))
            # Try older index as fallback
            if enable:
                DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            # No-op if unavailable
            pass

    def _add_bubble(self, text: str, sender: str):
        c = self.colors
        row = ttk.Frame(self.chat_frame)
        row.pack(fill="x", pady=6, padx=2)
        # subtle separator between messages
        sep = ttk.Separator(self.chat_frame, orient="horizontal")
        sep.pack(fill="x")
        inner = ttk.Frame(row)
        if sender == "user":
            inner.pack(anchor="e", padx=6)
            bg = c["user_bubble"]
        elif sender == "assistant":
            inner.pack(anchor="w", padx=6)
            bg = c["assistant_bubble"]
        else:
            inner.pack(anchor="center", padx=6)
            bg = c["panel"]
        # timestamp (muted)
        import datetime as _dt
        ts = _dt.datetime.now().strftime("%H:%M")
        ttk.Label(inner, text=ts, style="Muted.TLabel").pack(anchor=("w" if sender != "user" else "e"))
        # Bubble canvas for rounded background
        bubble_row = ttk.Frame(inner)
        bubble_row.pack(fill="x")
        canvas = tk.Canvas(bubble_row, bg=c["bg"], highlightthickness=0, bd=0, width=860, height=10)
        canvas.pack(side="left", fill="x", expand=True)
        # Create label for text
        lbl = tk.Label(canvas, text=text, wraplength=820, justify="left",
                       bg=bg, fg=c["text"], padx=14, pady=12, bd=0, highlightthickness=0, font=("Segoe UI", 10))
        # Measure and draw rounded rect then place label
        self.root.update_idletasks()
        lbl.update_idletasks()
        req_w = min(820, max(200, lbl.winfo_reqwidth()))
        req_h = max(34, lbl.winfo_reqheight())
        pad = 8
        canvas.configure(height=req_h + pad*2)
        self._draw_rounded_rect(canvas, 4, 4, req_w + pad*2, req_h + pad*2, 12, fill=bg, outline="")
        canvas.create_window(pad+4, pad+4, anchor="nw", window=lbl)
        if sender == "assistant":
            def do_copy(l=lbl):
                self.root.clipboard_clear()
                self.root.clipboard_append(l.cget("text"))
                self._set_status("Copied")
            btn = ttk.Button(bubble_row, text="Copy", style="Accent.TButton", command=do_copy)
            btn.pack(side="right", padx=(8,0))
            self._add_tooltip(btn, "Copy to clipboard")
            def on_enter(_): btn.configure(style="AccentHover.TButton")
            def on_leave(_): btn.configure(style="Accent.TButton")
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
        self.chat_bubbles.append((row, lbl, sender))
        # auto-scroll to bottom
        try:
            self.root.after(0, lambda: (self.chat_canvas.update_idletasks(), self.chat_canvas.yview_moveto(1)))
        except Exception:
            pass

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

    def _on_ctrl_enter(self, event):
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
        self._start_typing_indicator()
        self._run_setup_if_needed_then_generate(prompt)

    def _new_chat(self):
        # Clear chat bubbles and reset state
        for row, _, _ in self.chat_bubbles:
            try:
                row.destroy()
            except Exception:
                pass
        self.chat_bubbles.clear()
        self.current_assistant_label = None
        self._add_system_note("New chat started.")

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
                self._stop_typing_indicator()
        threading.Thread(target=task, daemon=True).start()

    def _start_typing_indicator(self):
        # Animate ellipsis in status during generation
        if self._typing_job:
            return
        dots = ["·  ", "·· ", "···", " ··", "  ·", "   "]
        i = {"n": 0}
        def tick():
            self.status_var.set("Generating " + dots[i["n"] % len(dots)])
            i["n"] += 1
            self._typing_job = self.root.after(300, tick)
        self._typing_job = self.root.after(300, tick)

    def _stop_typing_indicator(self):
        if self._typing_job:
            try:
                self.root.after_cancel(self._typing_job)
            except Exception:
                pass
            self._typing_job = None
        self.status_var.set("Done")

    def _draw_rounded_rect(self, canvas: tk.Canvas, x1, y1, x2, y2, r, **kwargs):
        # Draw a rounded rectangle on Canvas
        points = [
            x1+r, y1,
            x2-r, y1,
            x2, y1,
            x2, y1+r,
            x2, y2-r,
            x2, y2,
            x2-r, y2,
            x1+r, y2,
            x1, y2,
            x1, y2-r,
            x1, y1+r,
            x1, y1,
        ]
        # Approximate by drawing arcs + rectangles
        canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, style='pieslice', **kwargs)
        canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, style='pieslice', **kwargs)
        canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, style='pieslice', **kwargs)
        canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, style='pieslice', **kwargs)
        canvas.create_rectangle(x1+r, y1, x2-r, y2, **kwargs)
        canvas.create_rectangle(x1, y1+r, x2, y2-r, **kwargs)

    def _add_tooltip(self, widget, text: str):
        tip = _Tooltip(self.root, widget, text)
        self._tooltips.append(tip)

    def _parse_int(self, s: str):
        try:
            v = int(s)
            return v if v > 0 else None
        except Exception:
            return None

    def _set_status(self, text: str):
        self.status_var.set(text)


class _Tooltip:
    def __init__(self, root, widget, text: str):
        self.root = root
        self.widget = widget
        self.text = text
        self.tip = None
        try:
            widget.bind("<Enter>", self._show)
            widget.bind("<Leave>", self._hide)
        except Exception:
            pass

    def _show(self, _event=None):
        if self.tip:
            return
        try:
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self.tip = tk.Toplevel(self.root)
            self.tip.wm_overrideredirect(True)
            self.tip.wm_geometry(f"+{int(x)}+{int(y)}")
            lbl = tk.Label(self.tip, text=self.text, bg="#151a1e", fg="#eaf2f6", padx=8, pady=4, bd=0)
            lbl.pack()
        except Exception:
            self.tip = None

    def _hide(self, _event=None):
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None


def main():
    root = tk.Tk()
    VerdantGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main() 
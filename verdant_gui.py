#!/usr/bin/env python3
import threading
import tkinter as tk
from tkinter import messagebox
from tkinter import StringVar, filedialog
import tkinter.font as tkfont
import sys
import platform
import ctypes
from pathlib import Path

# Use ttkbootstrap for modern theming
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from verdant import (
    UserPreferences,
    ModelDownloader,
    HardwareDetector,
    AIInference,
    get_capabilities,
)

APP_TITLE = "Verdant Demo"

# Premium dark palette accents
ACCENT_BRAND = "#5BD174"
ACCENT_ALT = "#2AA198"

class VerdantGUI:
    def __init__(self, root: tk.Tk):
        # Re-wrap root into a themed ttkbootstrap window
        if not isinstance(root, tb.Window):
            # Use a dark, premium-looking theme
            root = tb.Window(themename="darkly")
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1080x720")
        self.root.minsize(860, 620)

        # Fonts
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=10)
        tkfont.nametofont("TkTextFont").configure(size=11)

        # State
        self.prefs_path = None
        self.prefs = UserPreferences.load(self.prefs_path)
        self.model_key = StringVar(value=self.prefs.get("model", "mistral-7b-q4"))
        self.status_var = StringVar(value="Ready")
        self.is_generating = False
        self.caps = get_capabilities()
        self.download_progress = tk.DoubleVar(value=0.0)
        self.chat_bubbles = []
        self.current_assistant_label = None
        self.chat_canvas = None
        self._typing_job = None
        self._tooltips = []
        self.char_count_var = StringVar(value="0 chars")
        # QoL state
        self._bubble_items = {}
        self._auto_scroll = True
        self._stop_requested = False
        self._last_user_prompt = ""
        self._is_regen = False
        self.chat_history = []  # list of {role: 'user'|'assistant', content: str}

        self._set_process_dpi_awareness()
        self._set_app_icon()
        self._set_app_user_model_id()
        self._apply_theme()
        self._build_ui()

    def _set_process_dpi_awareness(self):
        if platform.system() != "Windows":
            return
        try:
            DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
            ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        except Exception:
            try:
                PROCESS_PER_MONITOR_DPI_AWARE = 2
                ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
            except Exception:
                pass

    def _set_app_icon(self):
        try:
            here = Path(__file__).resolve().parent
            ico = here / "assets" / "icon" / "verdant.ico"
            if ico.exists():
                self.root.iconbitmap(default=str(ico))
        except Exception:
            pass

    def _set_app_user_model_id(self):
        if platform.system() != "Windows":
            return
        try:
            app_id = "Verdant.VerdantApp"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(app_id))
        except Exception:
            pass

    def _apply_theme(self):
        # Accent variables for bootstrap theme
        try:
            self.root.style.configure("Accent.TButton", bootstyle=SUCCESS)
            self.root.style.configure("Ghost.TButton", bootstyle=SECONDARY)
            self.root.style.configure("Icon.TButton", bootstyle=LINK)
            # Global selection colors for Text
            self.root.option_add("*selectBackground", ACCENT_ALT)
            self.root.option_add("*selectForeground", "#0b100d")
        except Exception:
            pass
        # Windows titlebar tweaks
        self._apply_titlebar_dark(True)
        self._apply_win11_backdrop_and_caption_colors()

    def _detect_system_theme(self) -> str:
        # Windows: AppsUseLightTheme = 0 → dark, 1 → light
        if platform.system() == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize")
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return "light" if int(val) == 1 else "dark"
            except Exception:
                return "dark"
        # macOS: prefer dark if AppleInterfaceStyle exists
        if platform.system() == "Darwin":
            try:
                import subprocess
                p = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"], capture_output=True, text=True)
                return "dark" if p.returncode == 0 and "Dark" in p.stdout else "light"
            except Exception:
                return "dark"
        # Linux/other: default dark
        return "dark"

    def _hex_to_colorref(self, hex_color: str) -> int:
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return b | (g << 8) | (r << 16)
        except Exception:
            return 0

    def _apply_titlebar_dark(self, enable: bool):
        if platform.system() != "Windows":
            return
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            val = ctypes.c_int(1 if enable else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(val), ctypes.sizeof(val))
            if enable:
                DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass

    def _apply_win11_backdrop_and_caption_colors(self):
        if platform.system() != "Windows":
            return
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            DWMWA_SYSTEMBACKDROP_TYPE = 38
            DWMSBT_MAINWINDOW = 2
            backdrop = ctypes.c_int(DWMSBT_MAINWINDOW)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(backdrop), ctypes.sizeof(backdrop))
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            # Use bootstrap window background/text
            bg = self.root.style.lookup("TFrame", "background") or "#0F1214"
            fg = self.root.style.lookup("TLabel", "foreground") or "#EAF2F6"
            caption = ctypes.c_int(self._hex_to_colorref(bg))
            textc = ctypes.c_int(self._hex_to_colorref(fg))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(caption), ctypes.sizeof(caption))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, ctypes.byref(textc), ctypes.sizeof(textc))
        except Exception:
            pass

    def _build_ui(self):
        # Use ttkbootstrap widgets
        self.root.columnconfigure(0, weight=0, minsize=240)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        sidebar = tb.Frame(self.root, bootstyle=SECONDARY)
        sidebar.grid(row=0, column=0, sticky="nswe")
        tb.Label(sidebar, text="Verdant", font=("Segoe UI Semibold", 14)).pack(anchor="w", padx=16, pady=(16, 4))
        tb.Label(sidebar, text="Eco‑Conscious Local AI", bootstyle=SECONDARY).pack(anchor="w", padx=16, pady=(0, 12))

        tb.Button(sidebar, text="⊕  New chat", bootstyle=SUCCESS, command=self._new_chat).pack(fill="x", padx=16, pady=(6, 6))
        tb.Button(sidebar, text="⤓  Export chat", bootstyle=SECONDARY, command=self._export_chat).pack(fill="x", padx=16, pady=(0, 6))
        tb.Button(sidebar, text="⧉  Copy all", bootstyle=SECONDARY, command=self._copy_all).pack(fill="x", padx=16, pady=(0, 6))

        tb.Separator(sidebar, orient="horizontal").pack(fill="x", padx=16, pady=(8, 8))
        badge = tb.Label(sidebar, text="Personal use • One‑time", bootstyle=SUCCESS)
        badge.pack(anchor="w", padx=16)
        tb.Label(sidebar, text="100% Local", bootstyle=SUCCESS).pack(anchor="w", padx=16, pady=(6,0))

        main = tb.Frame(self.root)
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(1, weight=1)
        main.columnconfigure(0, weight=1)

        header = tb.Frame(main)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        self.status_label = tb.Label(header, textvariable=self.status_var, bootstyle=SECONDARY)
        self.status_label.pack(side="left")
        settings_btn = tb.Button(header, text="⚙", bootstyle=LINK, width=3, command=self._open_settings)
        settings_btn.pack(side="right")
        self._add_tooltip(settings_btn, "Settings")
        self.setup_prog = tb.Progressbar(header, maximum=100, variable=self.download_progress, length=180, bootstyle=SUCCESS)
        self.setup_prog.pack(side="right", padx=(8,0))
        self.setup_prog.pack_forget()
        self.stop_btn = tb.Button(header, text="Stop", bootstyle=SECONDARY, command=self._on_stop)
        self.stop_btn.pack(side="right", padx=(8,8))
        self.stop_btn.pack_forget()
        self.regen_btn = tb.Button(header, text="Regenerate", bootstyle=SECONDARY, command=self._on_regenerate)
        self.regen_btn.pack(side="right", padx=(0,8))
        self.regen_btn.pack_forget()

        chat_wrap = tb.Frame(main)
        chat_wrap.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 6))
        main.rowconfigure(1, weight=1)
        self.chat_canvas = tk.Canvas(chat_wrap, highlightthickness=0, bg=self.root.style.lookup("TFrame", "background"))
        chat_scroll = tb.Scrollbar(chat_wrap, orient="vertical", command=self.chat_canvas.yview)
        self.chat_frame = tb.Frame(self.chat_canvas)
        self.chat_frame.bind("<Configure>", lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))
        self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        self.chat_canvas.configure(yscrollcommand=chat_scroll.set)
        self.chat_canvas.pack(side="left", fill="both", expand=True)
        chat_scroll.pack(side="right", fill="y")
        self.chat_canvas.bind("<Configure>", lambda e: (self._relayout_all_bubbles(), self._scroll_to_bottom()))

        input_wrap = tb.Frame(main)
        input_wrap.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        input_wrap.columnconfigure(0, weight=1)
        input_row = tb.Frame(input_wrap)
        input_row.grid(row=0, column=0, sticky="ew")
        input_row.columnconfigure(0, weight=1)
        self.input_text = tk.Text(input_row, height=3, wrap="word")
        self._style_text(self.input_text)
        self.input_text.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._attach_placeholder(self.input_text, "Message Verdant… (Enter/Ctrl+Enter to send; Shift+Enter = newline)")
        self.input_text.bind("<Return>", self._on_enter)
        self.input_text.bind("<Control-Return>", self._on_ctrl_enter)
        self.input_text.bind("<Shift-Return>", lambda e: self._insert_newline())
        self.input_text.bind("<KeyRelease>", self._update_char_count)
        self.input_text.bind("<Up>", self._recall_last_prompt)
        send_btn = tb.Button(input_row, text="➤", bootstyle=SUCCESS, width=4, command=self.on_send)
        send_btn.grid(row=0, column=1)
        self._add_tooltip(send_btn, "Send (Enter/Ctrl+Enter)")

        tb.Label(input_wrap, textvariable=self.char_count_var, bootstyle=SECONDARY).grid(row=1, column=0, sticky="e", pady=(4,0))

        self._add_system_note("Welcome to Verdant Demo — eco‑conscious local AI. Use Settings → Run Setup to download the model.")
        try:
            self.input_text.focus_set()
        except Exception:
            pass

    def _style_text(self, w: tk.Text):
        c = self.root.style.lookup("TFrame", "background") or "#0F1214"
        w.configure(bg=c, fg="#EAF2F6", insertbackground="#EAF2F6", highlightthickness=0, bd=0, padx=10, pady=8)

    def _attach_placeholder(self, w: tk.Text, text: str):
        c = self.root.style.lookup("TFrame", "background") or "#0F1214"
        def on_focus_in(_):
            if w.get("1.0", "end").strip() == text:
                w.delete("1.0", "end")
                w.configure(fg="#EAF2F6")
        def on_focus_out(_):
            if not w.get("1.0", "end").strip():
                w.insert("1.0", text)
                w.configure(fg="#9FB1BD")
        w.insert("1.0", text)
        w.configure(fg="#9FB1BD")
        w.bind("<FocusIn>", on_focus_in)
        w.bind("<FocusOut>", on_focus_out)

    def _add_bubble(self, text: str, sender: str):
        c = self.root.style.lookup("TFrame", "background") or "#0F1214"
        row = tb.Frame(self.chat_frame)
        row.pack(fill="x", pady=8, padx=6)
        inner = tb.Frame(row)
        if sender == "user":
            inner.pack(anchor="e", padx=6)
            bg = "#1D242A"
        elif sender == "assistant":
            inner.pack(anchor="w", padx=6)
            bg = "#0F2B1A"
        else:
            inner.pack(anchor="center", padx=6)
            bg = c
        import datetime as _dt
        ts = _dt.datetime.now().strftime("%H:%M")
        ttk.Label(inner, text=ts, style="Muted.TLabel").pack(anchor=("w" if sender != "user" else "e"))
        bubble_row = tb.Frame(inner)
        bubble_row.pack(fill="x")
        canvas = tk.Canvas(bubble_row, bg=c, highlightthickness=0, bd=0, width=860, height=10)
        canvas.pack(side="left", fill="x", expand=True)
        lbl = tk.Label(canvas, text=text, wraplength=820, justify="left",
                       bg=bg, fg="#EAF2F6", padx=14, pady=12, bd=0, highlightthickness=0, font=("Segoe UI", 11))
        self.root.update_idletasks()
        lbl.update_idletasks()
        req_w = min(820, max(260, lbl.winfo_reqwidth()))
        req_h = max(38, lbl.winfo_reqheight())
        pad = 10
        canvas.configure(height=req_h + pad*2)
        rect_id = self._draw_rounded_rect(canvas, 4, 4, req_w + pad*2, req_h + pad*2, 14, fill=bg, outline="")
        canvas.create_window(pad+4, pad+4, anchor="nw", window=lbl)
        # Track bubble for dynamic reflow and copying
        self._bubble_items[lbl] = (canvas, rect_id, pad)
        # Right-click to copy
        def _copy_event(_ev=None, l=lbl):
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(l.cget("text"))
                self._set_status("Copied")
            except Exception:
                pass
        lbl.bind("<Button-3>", _copy_event)
        if sender == "assistant":
            def do_copy(l=lbl):
                self.root.clipboard_clear()
                self.root.clipboard_append(l.cget("text"))
                self._set_status("Copied")
            btn = tb.Button(bubble_row, text="Copy", bootstyle=SECONDARY, command=do_copy)
            btn.pack(side="right", padx=(8,0))
            self._add_tooltip(btn, "Copy to clipboard")
            def on_enter(_): btn.configure(bootstyle=SUCCESS)
            def on_leave(_): btn.configure(bootstyle=SECONDARY)
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
        self.chat_bubbles.append((row, lbl, sender))
        try:
            self.root.after(0, self._scroll_to_bottom)
        except Exception:
            pass

    def _add_system_note(self, text: str):
        self._add_bubble(text, sender="system")

    def on_send(self):
        if self.is_generating:
            return
        prompt = self.input_text.get("1.0", "end").strip()
        if not prompt or prompt.startswith("Message Verdant…"):
            return
        self.input_text.delete("1.0", "end")
        self._update_char_count()
        self._add_bubble(prompt, sender="user")
        self._last_user_prompt = prompt
        self.chat_history.append({"role": "user", "content": prompt})
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
        self._stop_requested = False
        self._disable_send(True)
        self._add_bubble("", sender="assistant")
        self.current_assistant_label = self.chat_bubbles[-1][1]
        self._start_typing_indicator()
        try:
            self.stop_btn.pack(side="right", padx=(8,8))
            self.regen_btn.pack(side="right", padx=(0,8))
        except Exception:
            pass
        self._run_setup_if_needed_then_generate(prompt)

    def _new_chat(self):
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
                    if isinstance(child, tb.Button) and child.cget("text") in ("➤", "Send"):
                        child.configure(state=("disabled" if busy else "normal"))
            except Exception:
                continue

    def _open_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Settings")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.geometry("460x340")
        frame = tb.Frame(dlg, padding=12)
        frame.pack(fill="both", expand=True)
        tb.Label(frame, text="Model").pack(anchor="w")
        tb.Combobox(frame, textvariable=self.model_key, values=["mistral-7b-q4"], state="readonly").pack(fill="x", pady=(0, 12))
        # System status
        try:
            info = HardwareDetector.get_system_info()
            tier = HardwareDetector.get_performance_tier()
            caps = get_capabilities()
            rec_ctx = 4096 if tier == "high" else 2048 if tier == "medium" else 1024
            if isinstance(caps, dict) and isinstance(caps.get("max_context"), int):
                rec_ctx = min(rec_ctx, caps["max_context"])
            status = (
                f"Detected: {int(info['memory_gb'])}GB RAM, {info['cpu_count']} cores\n"
                f"Tier: {tier} • Recommended context: {rec_ctx}"
            )
            box = tb.Label(frame, text="System status", bootstyle=SECONDARY)
            box.pack(anchor="w")
            tb.Label(frame, text=status).pack(fill="x", pady=(0, 12))
        except Exception:
            pass
        btns = tb.Frame(frame)
        btns.pack(fill="x")
        tb.Button(btns, text="Save", command=self.on_save_prefs).pack(side="left")
        tb.Button(btns, text="Load", command=self.on_load_prefs).pack(side="left", padx=8)
        tb.Button(btns, text="Run Setup", bootstyle=SUCCESS, command=self.on_setup).pack(side="right")

    def on_save_prefs(self):
        prefs = {
            "model": self.model_key.get() or "mistral-7b-q4",
        }
        UserPreferences.save(prefs, self.prefs_path)
        self.status_var.set("Preferences saved")

    def on_load_prefs(self):
        self.prefs = UserPreferences.load(self.prefs_path)
        self.model_key.set(self.prefs.get("model", "mistral-7b-q4"))
        self.status_var.set("Preferences loaded")

    def on_setup(self):
        if self.is_generating:
            return
        self.status_var.set("Setting up…")
        self.download_progress.set(0)
        self.setup_prog.pack(side="right")
        self._disable_send(True)
        self.root.after(50, self._run_setup_async)

    def _run_setup_if_needed_then_generate(self, prompt: str):
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
                try:
                    self.setup_prog.pack_forget()
                except Exception:
                    pass
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
                ctx_model = self.model_key.get() or "mistral-7b-q4"
                dl = ModelDownloader()
                model_path = dl.get_model_path(ctx_model)
                if not model_path:
                    self._set_status("Model not found — run Setup first")
                    return
                ai = AIInference(model_path)
                # Build multi-turn prompt with system instruction and short history
                full_prompt = self._build_multiturn_prompt()
                accum = []
                def append_chunk(txt: str):
                    if self.current_assistant_label:
                        accum.append(txt)
                        current = self.current_assistant_label.cget("text")
                        self.current_assistant_label.configure(text=current + txt)
                        self._update_bubble_layout_for_label(self.current_assistant_label)
                        self._scroll_to_bottom()
                for chunk in ai.generate_response_stream(full_prompt):
                    if self._stop_requested:
                        break
                    self.root.after(0, append_chunk, chunk)
                # On finish, update history (replace last assistant on regen)
                final_text = "".join(accum)
                if not self._stop_requested:
                    if self._is_regen:
                        # Replace last assistant entry if exists
                        for i in range(len(self.chat_history)-1, -1, -1):
                            if self.chat_history[i]["role"] == "assistant":
                                self.chat_history[i]["content"] = final_text
                                break
                    else:
                        self.chat_history.append({"role": "assistant", "content": final_text})
                self._set_status("Done")
            except Exception as e:
                self._add_system_note(f"❌ Error: {e}")
                self._set_status("Error")
            finally:
                self.is_generating = False
                self._disable_send(False)
                self._stop_typing_indicator()
                try:
                    self.stop_btn.pack_forget()
                    self._is_regen = False
                except Exception:
                    pass
        threading.Thread(target=task, daemon=True).start()

    def _start_typing_indicator(self):
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
        canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, style='pieslice', **kwargs)
        canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, style='pieslice', **kwargs)
        canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, style='pieslice', **kwargs)
        canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, style='pieslice', **kwargs)
        canvas.create_rectangle(x1+r, y1, x2-r, y2, **kwargs)
        canvas.create_rectangle(x1, y1+r, x2, y2-r, **kwargs)
        # Return a new rectangle id to track (use last rectangle as base)
        return canvas.create_rectangle(x1+r, y1, x2-r, y2, outline="", fill=kwargs.get("fill", ""))

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

    def _update_char_count(self, _e=None):
        try:
            text = self.input_text.get("1.0", "end")
            n = len(text.strip())
            self.char_count_var.set(f"{n} chars")
        except Exception:
            self.char_count_var.set("0 chars")

    def _export_chat(self):
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
                title="Save chat transcript"
            )
            if not path:
                return
            lines = []
            for _, lbl, sender in self.chat_bubbles:
                if sender == "system":
                    prefix = "[system]"
                elif sender == "user":
                    prefix = "[user]"
                else:
                    prefix = "[assistant]"
                lines.append(f"{prefix} {lbl.cget('text')}")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(lines))
            self._set_status("Chat exported")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
            self._set_status("Export failed")

    def _scroll_to_bottom(self):
        try:
            if self._auto_scroll and self.chat_canvas:
                self.chat_canvas.update_idletasks()
                self.chat_canvas.yview_moveto(1)
        except Exception:
            pass

    def _update_bubble_layout_for_label(self, lbl: tk.Label):
        try:
            if lbl not in self._bubble_items:
                return
            canvas, rect_id, pad = self._bubble_items[lbl]
            # Adjust wraplength to canvas width minus padding
            avail = max(260, int(canvas.winfo_width()) - 40)
            lbl.configure(wraplength=avail)
            lbl.update_idletasks()
            req_w = min(avail, max(260, lbl.winfo_reqwidth()))
            req_h = max(38, lbl.winfo_reqheight())
            canvas.configure(height=req_h + pad*2)
            # Redraw rounded rect by updating its coords
            x1, y1 = 4, 4
            x2, y2 = req_w + pad*2, req_h + pad*2
            try:
                # Simplest: delete and redraw
                canvas.delete(rect_id)
                new_rect = self._draw_rounded_rect(canvas, x1, y1, x2, y2, 14, fill=lbl.cget("bg"), outline="")
                self._bubble_items[lbl] = (canvas, new_rect, pad)
            except Exception:
                pass
        except Exception:
            pass

    def _relayout_all_bubbles(self):
        try:
            for _, lbl, _ in self.chat_bubbles:
                self._update_bubble_layout_for_label(lbl)
        except Exception:
            pass

    def _on_stop(self):
        self._stop_requested = True
        self._set_status("Stopped")

    def _on_regenerate(self):
        if not self._last_user_prompt or not self.chat_bubbles:
            return
        # Remove last assistant history entry if present
        for i in range(len(self.chat_history)-1, -1, -1):
            if self.chat_history[i]["role"] == "assistant":
                del self.chat_history[i]
                break
        # Reuse last assistant bubble label
        last_row, last_lbl, last_sender = self.chat_bubbles[-1]
        if last_sender == "assistant":
            last_lbl.configure(text="")
            self.current_assistant_label = last_lbl
            self._is_regen = True
            self._stop_requested = False
            self.is_generating = True
            self._start_typing_indicator()
            try:
                self.stop_btn.pack(side="right", padx=(8,8))
            except Exception:
                pass
            # Run generation without adding another user bubble
            self._run_generate_async(self._last_user_prompt)

    def _recall_last_prompt(self, _event=None):
        try:
            if self._last_user_prompt:
                self.input_text.delete("1.0", "end")
                self.input_text.insert("1.0", self._last_user_prompt)
                self.input_text.see("1.0")
        except Exception:
            pass

    def _copy_all(self):
        try:
            lines = []
            for _, lbl, sender in self.chat_bubbles:
                if sender == "system":
                    prefix = "[system]"
                elif sender == "user":
                    prefix = "[user]"
                else:
                    prefix = "[assistant]"
                lines.append(f"{prefix} {lbl.cget('text')}")
            text = "\n\n".join(lines)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._set_status("Copied all")
        except Exception:
            pass

    def _build_multiturn_prompt(self) -> str:
        # Construct Mistral Instruct-style multi-turn prompt with minimal history
        sys_prompt = "You are Verdant, an eco-conscious local AI assistant. Be helpful, concise, and friendly."
        turns = []
        # Include up to last 3 user/assistant pairs
        pair_count = 0
        for msg in self.chat_history:
            if msg["role"] == "user":
                # Start a new pair
                content = msg["content"]
                if pair_count == 0:
                    # First pair includes system prompt
                    turns.append(f"<s>[INST] <<SYS>>{sys_prompt}<</SYS>> {content} [/INST]")
                else:
                    turns.append(f"<s>[INST] {content} [/INST]")
                pair_count += 1
            elif msg["role"] == "assistant":
                turns.append(msg["content"])
        # If last message is user without assistant yet, ensure the last INST is the live query
        if self.chat_history and self.chat_history[-1]["role"] == "user":
            # already captured in turns with [INST], no assistant following yet
            pass
        return "".join(turns)


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
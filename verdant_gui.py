#!/usr/bin/env python3
import threading
import tkinter as tk
from tkinter import messagebox
from tkinter import StringVar, filedialog
import tkinter.font as tkfont
import tkinter.ttk as ttk
import sys
import platform
import ctypes
from pathlib import Path
import json

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
from verdant import PresetsManager, run_benchmark

APP_TITLE = "Verdant"

# Premium dark palette accents
ACCENT_BRAND = "#1DB954"
ACCENT_ALT = "#179E4B"

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
        # New state
        self._active_preset = None
        cap_ctx = self.caps.get("max_context", 2048)
        try:
            cap_ctx = int(cap_ctx) if cap_ctx is not None else 2048
        except Exception:
            cap_ctx = 2048
        # Safely coerce prefs values (avoid int/float(None))
        self.temp_var = tk.DoubleVar(value=self._as_float(self.prefs.get("temperature", 0.7), 0.7))
        self.top_p_var = tk.DoubleVar(value=self._as_float(self.prefs.get("top_p", 0.9), 0.9))
        self.ctx_var = tk.IntVar(value=self._as_int(self.prefs.get("context"), cap_ctx))
        self.instant_demo_var = tk.BooleanVar(value=bool(self.prefs.get("instant_demo", True)))
        self.eco_savings_var = StringVar(value="🌿 0.00 Wh")
        self._eco_tokens_est = 0
        # Download metrics
        self._dl_last_bytes = 0
        self._dl_last_time = 0.0
        self._dl_total_bytes = 0

        self._set_process_dpi_awareness()
        self._set_app_icon()
        self._set_app_user_model_id()
        self._apply_theme()
        self._build_ui()
        # Maybe show onboarding on first launch if no model
        try:
            if not ModelDownloader().get_model_path(self.model_key.get() or "mistral-7b-q4") and not self.prefs.get("onboarded", False):
                self._open_onboarding()
        except Exception:
            pass

    def _as_int(self, value, default: int) -> int:
        try:
            if value is None:
                return default
            return int(value)
        except Exception:
            return default

    def _as_float(self, value, default: float) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

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
        self.root.columnconfigure(0, weight=0, minsize=280)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Enhanced Sidebar with better organization
        sidebar = tb.Frame(self.root, bootstyle=SECONDARY)
        sidebar.grid(row=0, column=0, sticky="nswe")
        
        # Header with logo and branding
        header_frame = tb.Frame(sidebar)
        header_frame.pack(fill="x", padx=16, pady=(16, 8))
        tb.Label(header_frame, text="🌿 Verdant", font=("Segoe UI Semibold", 16), bootstyle=SUCCESS).pack(anchor="w")
        tb.Label(header_frame, text="Eco‑Conscious Local AI", bootstyle=SECONDARY, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 12))
        
        # New Chat Section (Primary CTA)
        new_chat_frame = tb.Frame(sidebar)
        new_chat_frame.pack(fill="x", padx=16, pady=(0, 16))
        new_chat_btn = tb.Button(new_chat_frame, text="⊕  New Chat", bootstyle=SUCCESS, 
                 command=self._new_chat, font=("Segoe UI Semibold", 11))
        new_chat_btn.pack(fill="x")
        self._add_tooltip(new_chat_btn, "Start a new conversation (Ctrl+N)")
        
        # Conversation History Section
        history_frame = tb.Labelframe(sidebar, text="💬 Recent Chats", padding=8)
        history_frame.pack(fill="x", padx=16, pady=(0, 16))
        
        # Chat management buttons
        load_btn = tb.Button(history_frame, text="📥 Load Chat", bootstyle=SECONDARY, 
                 command=self._load_chat_json, width=20)
        load_btn.pack(fill="x", pady=(0, 4))
        self._add_tooltip(load_btn, "Load a saved chat (Ctrl+O)")
        
        save_btn = tb.Button(history_frame, text="💾 Save Chat", bootstyle=SECONDARY, 
                 command=self._save_chat_json, width=20)
        save_btn.pack(fill="x", pady=(0, 4))
        self._add_tooltip(save_btn, "Save current chat (Ctrl+S)")
        
        copy_btn = tb.Button(history_frame, text="⧉ Copy All", bootstyle=SECONDARY, 
                 command=self._copy_all, width=20)
        copy_btn.pack(fill="x", pady=(0, 4))
        self._add_tooltip(copy_btn, "Copy entire conversation (Ctrl+Shift+C)")
        
        export_btn = tb.Button(history_frame, text="⤓ Export Chat", bootstyle=SECONDARY, 
                 command=self._export_chat, width=20)
        export_btn.pack(fill="x", pady=(0, 4))
        self._add_tooltip(export_btn, "Export chat as text file (Ctrl+E)")
        
        # Custom GPTs Panel (if used)
        gpts_frame = tb.Labelframe(sidebar, text="🤖 AI Assistants", padding=8)
        gpts_frame.pack(fill="x", padx=16, pady=(0, 16))
        
        # Academic presets as custom GPTs
        paraphrase_btn = tb.Button(gpts_frame, text="📝 Paraphrase", bootstyle=SECONDARY, 
                 command=lambda: self._select_preset("paraphrase_academic"), width=20)
        paraphrase_btn.pack(fill="x", pady=(0, 4))
        self._add_tooltip(paraphrase_btn, "Academic paraphrasing assistant (Ctrl+1)")
        
        grammar_btn = tb.Button(gpts_frame, text="🔤 Grammar Fix", bootstyle=SECONDARY, 
                 command=lambda: self._select_preset("grammar_fix"), width=20)
        grammar_btn.pack(fill="x", pady=(0, 4))
        self._add_tooltip(grammar_btn, "Grammar and style assistant (Ctrl+2)")
        
        summary_btn = tb.Button(gpts_frame, text="📋 Summarize", bootstyle=SECONDARY, 
                 command=lambda: self._select_preset("concise_summary"), width=20)
        summary_btn.pack(fill="x", pady=(0, 4))
        self._add_tooltip(summary_btn, "Summarization assistant (Ctrl+3)")
        
        citation_btn = tb.Button(gpts_frame, text="📚 Citation Help", bootstyle=SECONDARY, 
                 command=lambda: self._select_preset("citation_check"), width=20)
        citation_btn.pack(fill="x", pady=(0, 4))
        self._add_tooltip(citation_btn, "Citation formatting assistant (Ctrl+4)")
        
        # Explore / Discover Section
        explore_frame = tb.Labelframe(sidebar, text="🔍 Explore & Discover", padding=8)
        explore_frame.pack(fill="x", padx=16, pady=(0, 16))
        
        # Sample prompts for discovery
        sample_prompts = [
            "Paraphrase: Social media affects students badly.",
            "Fix grammar: There going to the libary tommorow.",
            "Summarize: Paste a paragraph here.",
            "Citations: Convert these refs to APA: ...",
        ]
        
        for i, txt in enumerate(sample_prompts):
            btn = tb.Button(explore_frame, text=txt, bootstyle=LINK, 
                           command=lambda t=txt: self._insert_prompt(t), 
                           font=("Segoe UI", 8), anchor="w")
            btn.pack(fill="x", pady=(0, 2))
            # Add hover effect
            def on_enter(e, b=btn): b.configure(bootstyle=SUCCESS)
            def on_leave(e, b=btn): b.configure(bootstyle=LINK)
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            # Add tooltip with keyboard shortcut
            shortcut = f"Alt+{i+1}" if i < 9 else ""
            self._add_tooltip(btn, f"Try this prompt {shortcut}")

        # Settings and Help at bottom
        bottom_frame = tb.Frame(sidebar)
        bottom_frame.pack(fill="x", padx=16, pady=(16, 16), side="bottom")
        
        settings_btn = tb.Button(bottom_frame, text="⚙ Settings", bootstyle=SECONDARY, 
                 command=self._open_settings, width=20)
        settings_btn.pack(fill="x", pady=(0, 4))
        self._add_tooltip(settings_btn, "Open settings (Ctrl+,)")
        
        about_btn = tb.Button(bottom_frame, text="ℹ About", bootstyle=SECONDARY, 
                 command=self._open_about, width=20)
        about_btn.pack(fill="x")
        self._add_tooltip(about_btn, "About Verdant (F1)")

        # Main chat area
        main = tb.Frame(self.root)
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(1, weight=1)
        main.columnconfigure(0, weight=1)

        # Enhanced Top Bar with model selection and account info
        header = tb.Frame(main)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        
        # Left side: Status and eco meter
        left_header = tb.Frame(header)
        left_header.pack(side="left")
        self.status_label = tb.Label(left_header, textvariable=self.status_var, bootstyle=SECONDARY)
        self.status_label.pack(side="left")
        eco_lbl = tb.Label(left_header, textvariable=self.eco_savings_var, bootstyle=SUCCESS, 
                          font=("Segoe UI", 10))
        eco_lbl.pack(side="left", padx=(12, 0))
        
        # Center: Model selection and system message
        center_header = tb.Frame(header)
        center_header.pack(side="left", expand=True, fill="x", padx=20)
        
        # Model selector
        model_frame = tb.Frame(center_header)
        model_frame.pack(side="left")
        tb.Label(model_frame, text="Model:", bootstyle=SECONDARY, font=("Segoe UI", 9)).pack(side="left")
        model_combo = tb.Combobox(model_frame, textvariable=self.model_key, 
                                 values=["mistral-7b-q4"], state="readonly", 
                                 width=15, font=("Segoe UI", 9))
        model_combo.pack(side="left", padx=(4, 0))
        
        # System message status
        self.system_status_var = StringVar(value="This chat uses Mistral 7B Q4")
        system_lbl = tb.Label(center_header, textvariable=self.system_status_var, 
                             bootstyle=SECONDARY, font=("Segoe UI", 9))
        system_lbl.pack(side="left", padx=(20, 0))
        
        # Right side: Action buttons
        right_header = tb.Frame(header)
        right_header.pack(side="right")
        
        bench_btn = tb.Button(right_header, text="⚡", bootstyle=LINK, width=3, 
                             command=self._run_benchmark, font=("Segoe UI", 10))
        bench_btn.pack(side="right")
        self._add_tooltip(bench_btn, "Run benchmark (Ctrl+B)")
        
        self.setup_prog = tb.Progressbar(header, maximum=100, variable=self.download_progress, 
                                        length=180, bootstyle=SUCCESS)
        self.setup_prog.pack(side="right", padx=(8, 0))
        self.setup_prog.pack_forget()
        
        self.stop_btn = tb.Button(right_header, text="⏹ Stop", bootstyle=DANGER, 
                                 command=self._on_stop, font=("Segoe UI", 9))
        self.stop_btn.pack(side="right", padx=(8, 8))
        self.stop_btn.pack_forget()
        
        self.regen_btn = tb.Button(right_header, text="🔄 Regenerate", bootstyle=WARNING, 
                                  command=self._on_regenerate, font=("Segoe UI", 9))
        self.regen_btn.pack(side="right", padx=(0, 8))
        self.regen_btn.pack_forget()

        # Enhanced Chat Area with better visual hierarchy
        chat_wrap = tb.Frame(main)
        chat_wrap.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 6))
        main.rowconfigure(1, weight=1)
        
        # Chat canvas with improved styling
        self.chat_canvas = tk.Canvas(chat_wrap, highlightthickness=0, 
                                    bg=self.root.style.lookup("TFrame", "background"))
        chat_scroll = tb.Scrollbar(chat_wrap, orient="vertical", command=self.chat_canvas.yview)
        self.chat_frame = tb.Frame(self.chat_canvas)
        self.chat_frame.bind("<Configure>", lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))
        self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        self.chat_canvas.configure(yscrollcommand=chat_scroll.set)
        self.chat_canvas.pack(side="left", fill="both", expand=True)
        chat_scroll.pack(side="right", fill="y")
        self.chat_canvas.bind("<Configure>", lambda e: (self._relayout_all_bubbles(), self._scroll_to_bottom()))

        # Enhanced Input Area with better UX
        input_wrap = tb.Frame(main)
        input_wrap.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        input_wrap.columnconfigure(0, weight=1)
        
        # Input row with enhanced styling
        input_row = tb.Frame(input_wrap)
        input_row.grid(row=0, column=0, sticky="ew")
        input_row.columnconfigure(0, weight=1)
        
        # Enhanced input field with better visual feedback
        self.input_text = tk.Text(input_row, height=3, wrap="word", font=("Segoe UI", 11))
        self._style_text(self.input_text)
        self.input_text.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self._attach_placeholder(self.input_text, "Message Verdant… (Enter/Ctrl+Enter to send; Shift+Enter = newline)")
        self.input_text.bind("<Return>", self._on_enter)
        self.input_text.bind("<Control-Return>", self._on_ctrl_enter)
        self.input_text.bind("<Shift-Return>", lambda e: self._insert_newline())
        self.input_text.bind("<KeyRelease>", self._update_char_count)
        self.input_text.bind("<Up>", self._recall_last_prompt)
        
        # Enhanced send button with better visual hierarchy
        send_btn = tb.Button(input_row, text="➤ Send", bootstyle=SUCCESS, width=6, 
                            command=self.on_send, font=("Segoe UI Semibold", 10))
        send_btn.grid(row=0, column=1)
        self._add_tooltip(send_btn, "Send (Enter/Ctrl+Enter)")
        
        # Character count and input info
        input_info_frame = tb.Frame(input_wrap)
        input_info_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        input_info_frame.columnconfigure(1, weight=1)
        
        tb.Label(input_info_frame, textvariable=self.char_count_var, bootstyle=SECONDARY, 
                font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        
        # Input tips with dynamic suggestions
        self.tips_var = StringVar(value="💡 Tip: Use Shift+Enter for new lines, Ctrl+Enter to send quickly")
        tips_label = tb.Label(input_info_frame, textvariable=self.tips_var, bootstyle=SECONDARY, 
                             font=("Segoe UI", 8))
        tips_label.grid(row=0, column=1, sticky="e")
        
        # Store tips label for dynamic updates
        self.tips_label = tips_label

        self._add_system_note("Welcome to Verdant — eco‑conscious local AI. Use Settings → Run Setup to download the model, or try instant demo in Settings.")
        
        # Add centered hero logo in empty state
        try:
            if not self.chat_bubbles:
                logo_path = Path(__file__).resolve().parent / "assets" / "logo" / "verdant-wordmark.svg"
                # Fallback to ICO if SVG cannot be displayed in Tk; render via Pillow to PNG
                from PIL import Image, ImageTk
                png_path = logo_path.with_suffix('.png')
                if logo_path.exists():
                    try:
                        import cairosvg
                        if not png_path.exists():
                            cairosvg.svg2png(url=str(logo_path), write_to=str(png_path), output_width=480)
                    except Exception:
                        pass
                    if png_path.exists():
                        img = Image.open(str(png_path))
                        ph = ImageTk.PhotoImage(img)
                        logo_lbl = tk.Label(self.chat_canvas, image=ph, 
                                          bg=self.root.style.lookup("TFrame", "background"))
                        logo_lbl.image = ph
                        self.chat_canvas.create_window((self.chat_canvas.winfo_width()//2, 120), 
                                                     window=logo_lbl, anchor="n")
        except Exception:
            pass
        
        # Setup keyboard shortcuts
        self._setup_keyboard_shortcuts()
        
        try:
            self.input_text.focus_set()
        except Exception:
            pass

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for better accessibility"""
        # Global shortcuts
        self.root.bind("<Control-n>", lambda e: self._new_chat())
        self.root.bind("<Control-o>", lambda e: self._load_chat_json())
        self.root.bind("<Control-s>", lambda e: self._save_chat_json())
        self.root.bind("<Control-e>", lambda e: self._export_chat())
        self.root.bind("<Control-b>", lambda e: self._run_benchmark())
        self.root.bind("<Control-comma>", lambda e: self._open_settings())
        self.root.bind("<F1>", lambda e: self._open_about())
        
        # Preset shortcuts
        self.root.bind("<Control-1>", lambda e: self._select_preset("paraphrase_academic"))
        self.root.bind("<Control-2>", lambda e: self._select_preset("grammar_fix"))
        self.root.bind("<Control-3>", lambda e: self._select_preset("concise_summary"))
        self.root.bind("<Control-4>", lambda e: self._select_preset("citation_check"))
        
        # Alt shortcuts for sample prompts
        self.root.bind("<Alt-1>", lambda e: self._insert_prompt("Paraphrase: Social media affects students badly."))
        self.root.bind("<Alt-2>", lambda e: self._insert_prompt("Fix grammar: There going to the libary tommorow."))
        self.root.bind("<Alt-3>", lambda e: self._insert_prompt("Summarize: Paste a paragraph here."))
        self.root.bind("<Alt-4>", lambda e: self._insert_prompt("Citations: Convert these refs to APA: ..."))

    def _show_context_suggestions(self, prompt: str):
        """Show in-context suggestions based on user input"""
        prompt_lower = prompt.lower()
        suggestions = []
        
        if "paraphrase" in prompt_lower or "rewrite" in prompt_lower:
            suggestions.append("💡 Try: 'Paraphrase this text in a more formal academic tone'")
        elif "grammar" in prompt_lower or "fix" in prompt_lower:
            suggestions.append("💡 Try: 'Check and correct the grammar in this text'")
        elif "summarize" in prompt_lower or "summary" in prompt_lower:
            suggestions.append("💡 Try: 'Provide a concise 2-3 sentence summary'")
        elif "citation" in prompt_lower or "apa" in prompt_lower:
            suggestions.append("💡 Try: 'Convert these references to proper APA format'")
        elif len(prompt) < 10:
            suggestions.append("💡 Try asking about: paraphrasing, grammar, summaries, or citations")
        
        if suggestions:
            # Update tips with contextual suggestion
            self.tips_var.set(suggestions[0])
            # Auto-clear after 5 seconds
            self.root.after(5000, lambda: self.tips_var.set("💡 Tip: Use Shift+Enter for new lines, Ctrl+Enter to send quickly"))

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
            bg = "#13181C"
            border_color = "#1DB954"
        elif sender == "assistant":
            inner.pack(anchor="w", padx=6)
            bg = "#0E2518"
            border_color = "#179E4B"
        else:
            inner.pack(anchor="center", padx=6)
            bg = c
            border_color = "#2C3E50"
        
        # Enhanced bubble with better visual hierarchy
        bubble_row = tb.Frame(inner)
        bubble_row.pack(fill="x")
        
        # Main content canvas
        canvas = tk.Canvas(bubble_row, bg=c, highlightthickness=0, bd=0, width=860, height=10)
        canvas.pack(side="left", fill="x", expand=True)
        
        # Enhanced label with better typography
        lbl = tk.Label(canvas, text=text, wraplength=820, justify="left",
                       bg=bg, fg="#EAF2F6", padx=16, pady=14, bd=0, 
                       highlightthickness=0, font=("Segoe UI", 11))
        self.root.update_idletasks()
        lbl.update_idletasks()
        
        req_w = min(820, max(260, lbl.winfo_reqwidth()))
        req_h = max(38, lbl.winfo_reqheight())
        pad = 12
        
        canvas.configure(height=req_h + pad*2)
        
        # Enhanced rounded rectangle with subtle border
        rect_id = self._draw_rounded_rect(canvas, 4, 4, req_w + pad*2, req_h + pad*2, 16, 
                                        fill=bg, outline=border_color, width=1)
        canvas.create_window(pad+4, pad+4, anchor="nw", window=lbl)
        
        # Enhanced fade-in animation with smoother transitions
        try:
            alpha_steps = [int(x) for x in range(20, 101, 5)]
            def _fade(i=0):
                try:
                    if i < len(alpha_steps):
                        val = alpha_steps[i]
                        lbl.configure(fg="#EAF2F6")
                        canvas.itemconfig(rect_id, fill=bg)
                        self.root.after(12, lambda: _fade(i+1))
                except Exception:
                    pass
            self.root.after(0, _fade)
        except Exception:
            pass
        
        # Track bubble
        self._bubble_items[lbl] = (canvas, rect_id, pad)
        
        # Enhanced action buttons for assistant messages
        if sender == "assistant":
            # Action buttons frame
            actions_frame = tb.Frame(bubble_row)
            actions_frame.pack(side="right", padx=(8, 0))
            
            # Copy button
            copy_btn = tb.Button(actions_frame, text="📋 Copy", bootstyle=SECONDARY, 
                               command=lambda: self._copy_message(lbl), 
                               font=("Segoe UI", 8), width=8)
            copy_btn.pack(side="top", pady=(0, 4))
            self._add_tooltip(copy_btn, "Copy to clipboard")
            
            # Edit button (for user to edit their prompts)
            edit_btn = tb.Button(actions_frame, text="✏️ Edit", bootstyle=SECONDARY, 
                               command=lambda: self._edit_message(lbl), 
                               font=("Segoe UI", 8), width=8)
            edit_btn.pack(side="top", pady=(0, 4))
            self._add_tooltip(edit_btn, "Edit this message")
            
            # Feedback buttons
            feedback_frame = tb.Frame(actions_frame)
            feedback_frame.pack(side="top", pady=(0, 4))
            
            thumbs_up_btn = tb.Button(feedback_frame, text="👍", bootstyle=LINK, 
                                     command=lambda: self._give_feedback(lbl, "positive"), 
                                     font=("Segoe UI", 9), width=3)
            thumbs_up_btn.pack(side="left", padx=(0, 2))
            self._add_tooltip(thumbs_up_btn, "Good response")
            
            thumbs_down_btn = tb.Button(feedback_frame, text="👎", bootstyle=LINK, 
                                       command=lambda: self._give_feedback(lbl, "negative"), 
                                       font=("Segoe UI", 9), width=3)
            thumbs_down_btn.pack(side="left", padx=(2, 0))
            self._add_tooltip(thumbs_down_btn, "Poor response")
            
            # Hover effects for action buttons
            for btn in [copy_btn, edit_btn, thumbs_up_btn, thumbs_down_btn]:
                def on_enter(e, b=btn): 
                    if b.cget("text") in ["👍", "👎"]:
                        b.configure(bootstyle=SUCCESS)
                    else:
                        b.configure(bootstyle=SUCCESS)
                def on_leave(e, b=btn): 
                    if b.cget("text") in ["👍", "👎"]:
                        b.configure(bootstyle=LINK)
                    else:
                        b.configure(bootstyle=SECONDARY)
                btn.bind("<Enter>", on_enter)
                btn.bind("<Leave>", on_leave)
        
        # Right-click to copy for all messages
        def _copy_event(_ev=None, l=lbl):
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(l.cget("text"))
                self._set_status("Copied to clipboard")
            except Exception:
                pass
        lbl.bind("<Button-3>", _copy_event)
        
        # Add message to chat history
        self.chat_bubbles.append((row, lbl, sender))
        
        # Auto-scroll to bottom
        try:
            self.root.after(0, self._scroll_to_bottom)
        except Exception:
            pass

    def _add_system_note(self, text: str):
        self._add_bubble(text, sender="system")

    def on_send(self):
        """Enhanced send method with context suggestions"""
        if self.is_generating:
            return
        
        prompt = self.input_text.get("1.0", "end").strip()
        if not prompt or prompt.startswith("Message Verdant…"):
            return
        
        # Show context suggestions based on input
        self._show_context_suggestions(prompt)
        
        # Apply preset if any
        try:
            if self._active_preset:
                presets = PresetsManager.load_presets()
                ptext = presets.get(self._active_preset)
                if ptext:
                    prompt = f"{ptext}\n\n{prompt}"
        except Exception:
            pass
        
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
        """Enhanced generation start with better visual feedback"""
        self.status_var.set("Generating…")
        self.is_generating = True
        self._stop_requested = False
        self._disable_send(True)
        
        # Add assistant bubble with typing indicator
        self._add_bubble("", sender="assistant")
        self.current_assistant_label = self.chat_bubbles[-1][1]
        
        # Start enhanced typing indicator
        self._start_typing_indicator()
        
        # Show action buttons with better styling
        try:
            self.stop_btn.pack(side="right", padx=(8, 8))
            self.regen_btn.pack(side="right", padx=(0, 8))
        except Exception:
            pass
        
        # Add visual feedback to input area
        self.input_text.configure(state="disabled")
        
        # Start generation
        self._run_setup_if_needed_then_generate(prompt)

    def _on_generation_complete(self, response: str):
        """Enhanced generation completion with better UX"""
        try:
            # Stop typing indicator
            if self._typing_job:
                self.root.after_cancel(self._typing_job)
                self._typing_job = None
            
            # Update the assistant message
            if self.current_assistant_label:
                self.current_assistant_label.configure(text=response)
            
            # Add to chat history
            self.chat_history.append({"role": "assistant", "content": response})
            
            # Hide action buttons
            try:
                self.stop_btn.pack_forget()
                self.regen_btn.pack_forget()
            except Exception:
                pass
            
            # Re-enable input
            self.input_text.configure(state="normal")
            self.input_text.focus_set()
            
            # Update status with eco savings
            if self._eco_tokens_est > 0:
                self._set_status(f"Response complete! 🌿 Eco-friendly local processing")
            else:
                self._set_status("Response complete!")
            
            # Auto-scroll to show new message
            self._scroll_to_bottom()
            
        except Exception as e:
            self._set_status(f"Error displaying response: {e}")
        finally:
            self.is_generating = False
            self._disable_send(False)

    def _on_generation_error(self, error: str):
        """Enhanced error handling with better user feedback"""
        try:
            # Stop typing indicator
            if self._typing_job:
                self.root.after_cancel(self._typing_job)
                self._typing_job = None
            
            # Update the assistant message with error
            if self.current_assistant_label:
                error_text = f"❌ Sorry, I encountered an error:\n\n{error}\n\nPlease try again or check your settings."
                self.current_assistant_label.configure(text=error_text)
            
            # Hide action buttons
            try:
                self.stop_btn.pack_forget()
                self.regen_btn.pack_forget()
            except Exception:
                pass
            
            # Re-enable input
            self.input_text.configure(state="normal")
            self.input_text.focus_set()
            
            # Show helpful error status
            self._set_status(f"Generation failed: {error}")
            
        except Exception as e:
            self._set_status(f"Error handling failed: {e}")
        finally:
            self.is_generating = False
            self._disable_send(False)

    def _disable_send(self, busy: bool):
        """Enhanced send button state management"""
        try:
            # Find and update send button
            for widget in self.root.winfo_children():
                try:
                    for child in widget.winfo_children():
                        if isinstance(child, tb.Button) and "Send" in child.cget("text"):
                            if busy:
                                child.configure(state="disabled", bootstyle=SECONDARY)
                            else:
                                child.configure(state="normal", bootstyle=SUCCESS)
                            break
                except Exception:
                    continue
            
            # Update input field state
            if hasattr(self, 'input_text'):
                if busy:
                    self.input_text.configure(state="disabled")
                    # Add visual feedback
                    self.input_text.configure(bg="#2C3E50")
                else:
                    self.input_text.configure(state="normal")
                    # Restore normal appearance
                    self._style_text(self.input_text)
                    
        except Exception:
            pass

    def _new_chat(self):
        for row, _, _ in self.chat_bubbles:
            try:
                row.destroy()
            except Exception:
                pass
        self.chat_bubbles.clear()
        self.current_assistant_label = None
        self._add_system_note("New chat started.")

    def _open_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Settings - Verdant")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.geometry("520x480")
        dlg.resizable(False, False)
        
        # Main frame with padding
        frame = tb.Frame(dlg, padding=16)
        frame.pack(fill="both", expand=True)
        
        # Settings header
        header_frame = tb.Frame(frame)
        header_frame.pack(fill="x", pady=(0, 16))
        tb.Label(header_frame, text="⚙️ Settings", font=("Segoe UI Semibold", 16)).pack(side="left")
        
        # Create notebook for organized settings
        notebook = tb.Notebook(frame)
        notebook.pack(fill="both", expand=True)
        
        # General Settings Tab
        general_frame = tb.Frame(notebook, padding=16)
        notebook.add(general_frame, text="General")
        
        # Model selection
        model_section = tb.Labelframe(general_frame, text="🤖 AI Model", padding=12)
        model_section.pack(fill="x", pady=(0, 16))
        tb.Label(model_section, text="Model:").pack(anchor="w")
        tb.Combobox(model_section, textvariable=self.model_key, 
                   values=["mistral-7b-q4"], state="readonly").pack(fill="x", pady=(0, 12))
        
        # Theme selection
        theme_section = tb.Labelframe(general_frame, text="🎨 Appearance", padding=12)
        theme_section.pack(fill="x", pady=(0, 16))
        
        # Theme toggle
        self.theme_var = StringVar(value="dark")
        theme_frame = tb.Frame(theme_section)
        theme_frame.pack(fill="x")
        tb.Label(theme_frame, text="Theme:").pack(side="left")
        tb.Radiobutton(theme_frame, text="🌙 Dark", variable=self.theme_var, 
                      value="dark", command=self._apply_theme_setting).pack(side="left", padx=(20, 0))
        tb.Radiobutton(theme_frame, text="☀️ Light", variable=self.theme_var, 
                      value="light", command=self._apply_theme_setting).pack(side="left", padx=(20, 0))
        tb.Radiobutton(theme_frame, text="🔄 Auto", variable=self.theme_var, 
                      value="auto", command=self._apply_theme_setting).pack(side="left", padx=(20, 0))
        
        # Generation Controls Tab
        controls_frame = tb.Frame(notebook, padding=16)
        notebook.add(controls_frame, text="Generation")
        
        # Generation controls
        ctrls = tb.Labelframe(controls_frame, text="🎛️ Generation Parameters", padding=12)
        ctrls.pack(fill="x", pady=(0, 16))
        
        # Temperature control
        temp_frame = tb.Frame(ctrls)
        temp_frame.pack(fill="x", pady=(0, 8))
        tb.Label(temp_frame, text=f"Temperature: {self.temp_var.get():.2f}").pack(side="left")
        temp_scale = tb.Scale(temp_frame, from_=0.0, to=1.2, orient="horizontal", 
                             value=self.temp_var.get(), 
                             command=lambda v: self.temp_var.set(float(v)))
        temp_scale.pack(side="right", fill="x", expand=True, padx=(20, 0))
        
        # Top-p control
        top_p_frame = tb.Frame(ctrls)
        top_p_frame.pack(fill="x", pady=(0, 8))
        top_p_frame.columnconfigure(1, weight=1)
        tb.Label(top_p_frame, text=f"Top‑p: {self.top_p_var.get():.2f}").pack(side="left")
        top_p_scale = tb.Scale(top_p_frame, from_=0.1, to=1.0, orient="horizontal", 
                              value=self.top_p_var.get(), 
                              command=lambda v: self.top_p_var.set(float(v)))
        top_p_scale.pack(side="right", fill="x", expand=True, padx=(20, 0))
        
        # Context control
        max_ctx = int(self.caps.get("max_context", 2048))
        ctx_frame = tb.Frame(ctrls)
        ctx_frame.pack(fill="x", pady=(0, 8))
        ctx_frame.columnconfigure(1, weight=1)
        tb.Label(ctx_frame, text=f"Context: {self.ctx_var.get()} (max {max_ctx})").pack(side="left")
        ctx_scale = tb.Scale(ctx_frame, from_=256, to=max_ctx, orient="horizontal", 
                            value=self.ctx_var.get(), 
                            command=lambda v: self.ctx_var.set(int(float(v))))
        ctx_scale.pack(side="right", fill="x", expand=True, padx=(20, 0))
        
        # Demo options
        opt = tb.Labelframe(controls_frame, text="🚀 Demo Options", padding=12)
        opt.pack(fill="x", pady=(0, 16))
        inst = tb.Checkbutton(opt, text="Enable instant demo (no download)", 
                             variable=self.instant_demo_var, bootstyle=SECONDARY)
        inst.pack(anchor="w")
        
        # System Status Tab
        status_frame = tb.Frame(notebook, padding=16)
        notebook.add(status_frame, text="System")
        
        # System status
        try:
            info = HardwareDetector.get_system_info()
            tier = HardwareDetector.get_performance_tier()
            caps = get_capabilities()
            rec_ctx = 4096 if tier == "high" else 2048 if tier == "medium" else 1024
            if isinstance(caps, dict) and isinstance(caps.get("max_context"), int):
                rec_ctx = min(rec_ctx, caps["max_context"])
            
            status_text = (
                f"💻 System Information:\n"
                f"   • RAM: {int(info['memory_gb'])}GB\n"
                f"   • CPU Cores: {info['cpu_count']}\n"
                f"   • Performance Tier: {tier.title()}\n"
                f"   • Recommended Context: {rec_ctx}\n\n"
                f"🔧 Capabilities:\n"
                f"   • Max Context: {caps.get('max_context', 'Unknown')}\n"
                f"   • GPU Support: {'Yes' if caps.get('allow_gpu') else 'No'}\n"
                f"   • Document Tools: {'Yes' if caps.get('allow_doc_tools') else 'No'}"
            )
            
            status_box = tb.Labelframe(status_frame, text="System Status", padding=12)
            status_box.pack(fill="x", pady=(0, 16))
            tb.Label(status_box, text=status_text, justify="left").pack(fill="x")
            
        except Exception as e:
            tb.Label(status_frame, text=f"Unable to load system information: {e}", 
                    bootstyle=DANGER).pack()
        
        # Privacy & Data Controls
        privacy_frame = tb.Labelframe(status_frame, text="🔒 Privacy & Data", padding=12)
        privacy_frame.pack(fill="x", pady=(0, 16))
        
        # Data export
        tb.Button(privacy_frame, text="📤 Export All Data", bootstyle=SECONDARY, 
                 command=self._export_all_data, width=20).pack(fill="x", pady=(0, 4))
        
        # Data deletion
        tb.Button(privacy_frame, text="🗑️ Clear Chat History", bootstyle=DANGER, 
                 command=self._clear_chat_history, width=20).pack(fill="x", pady=(0, 4))
        
        # Notification settings
        tb.Button(privacy_frame, text="🔔 Notification Settings", bootstyle=SECONDARY, 
                 command=self._open_notification_settings, width=20).pack(fill="x", pady=(0, 4))
        
        # Bottom buttons
        btns = tb.Frame(frame)
        btns.pack(fill="x", pady=(16, 0))
        
        # Left side buttons
        left_btns = tb.Frame(btns)
        left_btns.pack(side="left")
        tb.Button(left_btns, text="💾 Save", command=self.on_save_prefs, 
                 bootstyle=SUCCESS).pack(side="left", padx=(0, 8))
        tb.Button(left_btns, text="📂 Load", command=self.on_load_prefs, 
                 bootstyle=SECONDARY).pack(side="left")
        
        # Right side buttons
        right_btns = tb.Frame(btns)
        right_btns.pack(side="right")
        tb.Button(right_btns, text="🚀 Run Setup", bootstyle=SUCCESS, 
                 command=self.on_setup).pack(side="right")
        tb.Button(right_btns, text="❌ Close", bootstyle=SECONDARY, 
                 command=dlg.destroy).pack(side="right", padx=(0, 8))

    def on_save_prefs(self):
        prefs = {
            "model": self.model_key.get() or "mistral-7b-q4",
            "temperature": float(self.temp_var.get()),
            "top_p": float(self.top_p_var.get()),
            "context": int(self.ctx_var.get()),
            "instant_demo": bool(self.instant_demo_var.get()),
            "onboarded": True,
        }
        UserPreferences.save(prefs, self.prefs_path)
        self.status_var.set("Preferences saved")

    def on_load_prefs(self):
        self.prefs = UserPreferences.load(self.prefs_path)
        self.model_key.set(self.prefs.get("model", "mistral-7b-q4"))
        self.temp_var.set(self._as_float(self.prefs.get("temperature", 0.7), 0.7))
        self.top_p_var.set(self._as_float(self.prefs.get("top_p", 0.9), 0.9))
        cap_ctx = self.caps.get("max_context", 2048)
        try:
            cap_ctx = int(cap_ctx) if cap_ctx is not None else 2048
        except Exception:
            cap_ctx = 2048
        self.ctx_var.set(self._as_int(self.prefs.get("context"), cap_ctx))
        self.instant_demo_var.set(bool(self.prefs.get("instant_demo", True)))
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
        """Enhanced setup and generation flow"""
        def task():
            try:
                # Check if we need to download the model
                model = self.model_key.get() or "mistral-7b-q4"
                dl = ModelDownloader()
                mp = dl.get_model_path(model)
                
                if not mp and not self.instant_demo_var.get():
                    # Need to download model
                    self._set_status("Downloading model...")
                    self.setup_prog.pack(side="right", padx=(8, 0))
                    
                    # Download with progress updates
                    def progress_callback(bytes_downloaded, total_bytes):
                        if total_bytes > 0:
                            progress = (bytes_downloaded / total_bytes) * 100
                            self.download_progress.set(progress)
                            self.root.update_idletasks()
                    
                    mp = dl.download_model(model, progress_callback=progress_callback)
                    self.setup_prog.pack_forget()
                    
                    if not mp:
                        self._set_status("Model download failed")
                        self._on_generation_error("Failed to download AI model. Please check your internet connection and try again.")
                        return
                
                # Generate response
                if self.instant_demo_var.get() and not mp:
                    # Use instant demo
                    response = self._generate_demo_response(prompt)
                    self.root.after(0, lambda: self._on_generation_complete(response))
                else:
                    # Use local model
                    ai = AIInference(mp, n_ctx=int(self.ctx_var.get()))
                    response = ai.generate(prompt, 
                                        temperature=float(self.temp_var.get()),
                                        top_p=float(self.top_p_var.get()))
                    self.root.after(0, lambda: self._on_generation_complete(response))
                    
            except Exception as e:
                error_msg = str(e)
                self._set_status(f"Generation error: {error_msg}")
                self.root.after(0, lambda: self._on_generation_error(error_msg))
        
        # Run in background thread
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
                self._dl_last_bytes = 0
                self._dl_last_time = 0.0
                self._dl_total_bytes = 0
        threading.Thread(target=task, daemon=True).start()

    def _on_download_progress(self, percent: float, downloaded: int, total: int):
        try:
            self._dl_total_bytes = total
            import time as _t
            now = _t.time()
            bps = 0.0
            if self._dl_last_time:
                elapsed = max(1e-3, now - self._dl_last_time)
                bps = max(0.0, (downloaded - self._dl_last_bytes) / elapsed)
            self._dl_last_bytes = downloaded
            self._dl_last_time = now
            mbps = bps / (1024*1024)
            eta_s = int(((total - downloaded) / bps)) if bps > 0 else 0
            mm = eta_s // 60
            ss = eta_s % 60
            self.status_var.set(f"Downloading… {percent:.1f}% • {downloaded/(1024*1024):.1f}/{total/(1024*1024):.1f} MB • {mbps:.2f} MB/s • ETA {mm:02d}:{ss:02d}")
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
                    self._set_status("Model not found — run Setup or enable instant demo")
                    return
                ai = AIInference(model_path, n_ctx=int(self.ctx_var.get()), n_threads=None, temperature=float(self.temp_var.get()), top_p=float(self.top_p_var.get()))
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
                # Update eco meter (very rough estimate: 1 word ~ 1 token, 1e-4 Wh/token saved)
                try:
                    tokens_est = max(1, len(final_text.split()))
                    self._eco_tokens_est += tokens_est
                    saved_wh = self._eco_tokens_est * 1e-4 * 0.95
                    self.eco_savings_var.set(f"🌿 {saved_wh:.2f} Wh")
                except Exception:
                    pass
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

    def _run_demo_generate_async(self, prompt: str):
        def task():
            try:
                # Simulate streaming canned response for instant demo
                preset_text = None
                try:
                    presets = PresetsManager.load_presets()
                    if self._active_preset and self._active_preset in presets:
                        preset_text = presets[self._active_preset]
                except Exception:
                    pass
                intro = "This is instant demo mode (no model download)."
                body = "\n" + (preset_text + "\n\n" if preset_text else "") + "Here is a helpful response to your prompt: " + prompt[:200]
                chunks = [intro + "\n", body, "\n\nUpgrade to full model for higher quality responses."]
                for ch in chunks:
                    if self.current_assistant_label:
                        cur = self.current_assistant_label.cget("text")
                        self.current_assistant_label.configure(text=cur + ch)
                        self._update_bubble_layout_for_label(self.current_assistant_label)
                        self._scroll_to_bottom()
                        import time as _t; _t.sleep(0.2)
                # Update eco meter modestly
                self._eco_tokens_est += 80
                saved_wh = self._eco_tokens_est * 1e-4 * 0.95
                self.eco_savings_var.set(f"🌿 {saved_wh:.2f} Wh")
                self._set_status("Done (demo)")
            except Exception as e:
                self._add_system_note(f"❌ Demo error: {e}")
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
        """Enhanced typing indicator with better visual feedback"""
        if not self.current_assistant_label:
            return
        
        try:
            # Create typing animation frame
            typing_frame = tb.Frame(self.current_assistant_label.master)
            typing_frame.pack(side="left", padx=(8, 0))
            
            # Typing dots animation
            dots = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            dot_label = tk.Label(typing_frame, text="", font=("Segoe UI", 16), 
                               fg="#1DB954", bg=self.root.style.lookup("TFrame", "background"))
            dot_label.pack()
            
            # Animate dots
            def animate_dots(i=0):
                if self._stop_requested or not self.is_generating:
                    try:
                        typing_frame.destroy()
                    except Exception:
                        pass
                    return
                
                dot_label.configure(text=dots[i % len(dots)])
                self._typing_job = self.root.after(120, lambda: animate_dots(i + 1))
            
            animate_dots()
            
        except Exception:
            pass

    def _stop_typing_indicator(self):
        """Stop the typing indicator animation"""
        if self._typing_job:
            try:
                self.root.after_cancel(self._typing_job)
                self._typing_job = None
            except Exception:
                pass

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

    def _set_status(self, message: str):
        self.status_var.set(message)
        
        # Auto-clear status after 3 seconds for non-critical messages
        if message not in ["Generating…", "Setting up…", "Ready"]:
            self.root.after(3000, lambda: self.status_var.set("Ready"))

    def _update_char_count(self, _e=None):
        try:
            text = self.input_text.get("1.0", "end")
            n = len(text.strip())
            self.char_count_var.set(f"{n} chars")
        except Exception:
            self.char_count_var.set("0 chars")

    def _export_chat(self):
        try:
            path = filedialog.asksaveasfilename(defaultextension=".txt", 
                                              filetypes=[("Text", "*.txt"), ("All Files", "*.*")], 
                                              title="Export chat as text")
            if not path:
                return
            content = []
            for _, lbl, sender in self.chat_bubbles:
                if sender == "user":
                    content.append(f"User: {lbl.cget('text')}")
                elif sender == "assistant":
                    content.append(f"Verdant: {lbl.cget('text')}")
                else:
                    content.append(f"System: {lbl.cget('text')}")
                content.append("")  # Empty line between messages
            
            Path(path).write_text("\n".join(content), encoding="utf-8")
            self._set_status("Chat exported")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
            self._set_status("Export failed")

    def _scroll_to_bottom(self):
        """Enhanced scroll to bottom with smooth animation"""
        if not self._auto_scroll:
            return
        try:
            # Smooth scroll animation
            current_pos = self.chat_canvas.yview()[1]
            target_pos = 1.0
            if abs(current_pos - target_pos) > 0.01:
                new_pos = current_pos + (target_pos - current_pos) * 0.3
                self.chat_canvas.yview_moveto(new_pos)
                if abs(new_pos - target_pos) > 0.01:
                    self.root.after(16, self._scroll_to_bottom)
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
        """Relayout all chat bubbles when window is resized"""
        try:
            for lbl, (canvas, rect_id, pad) in self._bubble_items.items():
                # Recalculate bubble dimensions
                req_w = min(820, max(260, lbl.winfo_reqwidth()))
                req_h = max(38, lbl.winfo_reqheight())
                canvas.configure(width=req_w + pad*2, height=req_h + pad*2)
                
                # Update rounded rectangle
                canvas.coords(rect_id, 4, 4, req_w + pad*2 + 4, req_h + pad*2 + 4)
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
        """Copy all chat messages to clipboard"""
        try:
            content = []
            for _, lbl, sender in self.chat_bubbles:
                if sender == "user":
                    content.append(f"User: {lbl.cget('text')}")
                elif sender == "assistant":
                    content.append(f"Verdant: {lbl.cget('text')}")
                else:
                    content.append(f"System: {lbl.cget('text')}")
                content.append("")  # Empty line between messages
            
            all_text = "\n".join(content)
            self.root.clipboard_clear()
            self.root.clipboard_append(all_text)
            self._set_status("All messages copied to clipboard")
        except Exception as e:
            self._set_status("Failed to copy messages")

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

    def _select_preset(self, preset_name: str):
        """Select a preset and show visual feedback"""
        try:
            self._active_preset = preset_name
            preset_names = {
                "paraphrase_academic": "Academic Paraphrasing",
                "grammar_fix": "Grammar & Style",
                "concise_summary": "Summarization",
                "citation_check": "Citation Help"
            }
            preset_display = preset_names.get(preset_name, preset_name)
            self._set_status(f"Selected preset: {preset_display}")
            
            # Show context suggestion
            if preset_name == "paraphrase_academic":
                self.tips_var.set("💡 Now type or paste the text you want to paraphrase")
            elif preset_name == "grammar_fix":
                self.tips_var.set("💡 Now type or paste the text you want to check")
            elif preset_name == "concise_summary":
                self.tips_var.set("💡 Now type or paste the text you want to summarize")
            elif preset_name == "citation_check":
                self.tips_var.set("💡 Now type or paste the references you want to format")
            
            # Auto-clear suggestion after 5 seconds
            self.root.after(5000, lambda: self.tips_var.set("💡 Tip: Use Shift+Enter for new lines, Ctrl+Enter to send quickly"))
            
        except Exception:
            pass

    def _insert_prompt(self, text: str):
        """Insert a prompt into the input field"""
        try:
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", text)
            self.input_text.focus_set()
            self._set_status("Prompt inserted")
        except Exception:
            pass

    def _open_onboarding(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Welcome to Verdant! 🌿")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.geometry("500x400")
        dlg.resizable(False, False)
        
        # Center the dialog
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth() // 2) - (500 // 2)
        y = (dlg.winfo_screenheight() // 2) - (400 // 2)
        dlg.geometry(f"500x400+{x}+{y}")
        
        # Main frame with padding
        frame = tb.Frame(dlg, padding=20)
        frame.pack(fill="both", expand=True)
        
        # Welcome header
        header_frame = tb.Frame(frame)
        header_frame.pack(fill="x", pady=(0, 24))
        
        tb.Label(header_frame, text="🌿 Welcome to Verdant!", 
                font=("Segoe UI Semibold", 20), bootstyle=SUCCESS).pack()
        tb.Label(header_frame, text="Your eco-conscious local AI assistant", 
                font=("Segoe UI", 12), bootstyle=SECONDARY).pack(pady=(4, 0))
        
        # Welcome message
        welcome_text = (
            "Verdant runs completely on your device, ensuring:\n"
            "• 🔒 100% privacy - no data sent to the cloud\n"
            "• 🌱 95% less energy than cloud AI\n"
            "• ⚡ Instant responses - no internet required\n"
            "• 🎓 Perfect for students and academics"
        )
        
        welcome_frame = tb.Labelframe(frame, text="✨ Why Choose Verdant?", padding=16)
        welcome_frame.pack(fill="x", pady=(0, 24))
        
        for line in welcome_text.split('\n'):
            if line.strip():
                tb.Label(welcome_frame, text=line, justify="left", 
                        font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 2))
        
        # Setup steps
        steps_frame = tb.Labelframe(frame, text="🚀 Getting Started", padding=16)
        steps_frame.pack(fill="x", pady=(0, 24))
        
        steps = [
            "1️⃣ Choose your setup option below",
            "2️⃣ Download the AI model (~3.8GB, one-time)",
            "3️⃣ Start chatting locally with instant responses"
        ]
        
        for step in steps:
            tb.Label(steps_frame, text=step, justify="left", 
                    font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))
        
        # Action buttons
        btns_frame = tb.Frame(frame)
        btns_frame.pack(fill="x", pady=(0, 16))
        
        # Primary CTA - Run Setup
        setup_btn = tb.Button(btns_frame, text="🚀 Run Setup & Download Model", 
                             bootstyle=SUCCESS, font=("Segoe UI Semibold", 11),
                             command=lambda: (dlg.destroy(), self.on_setup()))
        setup_btn.pack(fill="x", pady=(0, 8))
        
        # Secondary options
        options_frame = tb.Frame(btns_frame)
        options_frame.pack(fill="x")
        
        # Try instant demo
        demo_btn = tb.Button(options_frame, text="🎭 Try Instant Demo", 
                            bootstyle=SECONDARY, font=("Segoe UI", 10),
                            command=lambda: (self.instant_demo_var.set(True), 
                                           self._set_status("Instant demo enabled"), 
                                           dlg.destroy()))
        demo_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        # Skip for now
        skip_btn = tb.Button(options_frame, text="⏭️ Skip for Now", 
                            bootstyle=LINK, font=("Segoe UI", 10),
                            command=dlg.destroy)
        skip_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))
        
        # Footer note
        footer_frame = tb.Frame(frame)
        footer_frame.pack(fill="x", side="bottom")
        
        tb.Label(footer_frame, text="💡 Tip: You can always run setup later from Settings → Run Setup", 
                font=("Segoe UI", 9), bootstyle=SECONDARY, justify="center").pack()
        
        # Mark as onboarded on close
        def _mark_onboarded(_e=None):
            try:
                p = UserPreferences.load(self.prefs_path)
                p["onboarded"] = True
                UserPreferences.save(p, self.prefs_path)
            except Exception:
                pass
        
        dlg.protocol("WM_DELETE_WINDOW", lambda: (_mark_onboarded(), dlg.destroy()))
        
        # Focus on the primary button
        setup_btn.focus_set()

    def _run_benchmark(self):
        if self.is_generating:
            return
        def task():
            try:
                model = self.model_key.get() or "mistral-7b-q4"
                dl = ModelDownloader()
                mp = dl.get_model_path(model)
                if not mp:
                    self._set_status("Model not found — run Setup")
                    return
                ai = AIInference(mp, n_ctx=int(self.ctx_var.get()))
                run_benchmark(ai, runs=1)
                self._set_status("Benchmark complete")
            except Exception as e:
                self._set_status(f"Benchmark error: {e}")
        threading.Thread(target=task, daemon=True).start()

    def _open_about(self):
        try:
            base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
            ver = (base / "version.txt").read_text(encoding="utf-8").strip() if (base / "version.txt").exists() else "v0.0.0"
            chan = (base / "channel.txt").read_text(encoding="utf-8").strip() if (base / "channel.txt").exists() else "demo"
            messagebox.showinfo("About Verdant", f"Verdant Demo\nVersion: {ver}\nChannel: {chan}\n\n100% local. 95% less energy than cloud AI.")
        except Exception:
            pass

    def _save_chat_json(self):
        try:
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json"), ("All Files", "*.*")], title="Save chat as JSON")
            if not path:
                return
            data = {"history": self.chat_history, "saved_at": __import__("time").time(), "version": "1.0"}
            Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
            self._set_status("Chat saved")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            self._set_status("Save failed")

    def _load_chat_json(self):
        try:
            path = filedialog.askopenfilename(filetypes=[["JSON", "*.json"], ["All Files", "*.*"]], title="Load chat JSON")
            if not path:
                return
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.chat_history = data.get("history", [])
            # Repaint bubbles from history
            for row, _, _ in list(self.chat_bubbles):
                try: row.destroy()
                except Exception: pass
            self.chat_bubbles.clear()
            for msg in self.chat_history:
                self._add_bubble(msg.get("content", ""), sender=("user" if msg.get("role") == "user" else "assistant"))
            self._set_status("Chat loaded")
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            self._set_status("Load failed")

    def _copy_message(self, lbl: tk.Label):
        """Copy a specific message to clipboard"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(lbl.cget("text"))
            self._set_status("Copied to clipboard")
        except Exception:
            pass

    def _edit_message(self, lbl: tk.Label):
        """Edit a message by putting it back in the input field"""
        try:
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", lbl.cget("text"))
            self.input_text.focus_set()
            self._set_status("Message loaded for editing")
        except Exception:
            pass

    def _give_feedback(self, lbl: tk.Label, feedback_type: str):
        """Give feedback on a message (thumbs up/down)"""
        # In a real application, you would send this feedback to your backend
        # For this demo, we'll just log it and show status
        print(f"Feedback received: {feedback_type} for message: {lbl.cget('text')}")
        self._set_status(f"Feedback received: {feedback_type}")
        
        # Visual feedback - change button appearance
        if feedback_type == "positive":
            self._set_status("👍 Thank you for the positive feedback!")
        else:
            self._set_status("👎 Thank you for the feedback. We'll work to improve!")

    def _generate_demo_response(self, prompt: str):
        """Generate a demo response when no model is available"""
        # Simple demo responses for common academic tasks
        prompt_lower = prompt.lower()
        
        if "paraphrase" in prompt_lower:
            return ("Here's a paraphrased version of your text:\n\n"
                   "This is a demo response showing how Verdant would paraphrase text. "
                   "In the full version, you would get an actual AI-generated paraphrase "
                   "of your specific text.\n\n"
                   "To get real AI responses, download the model using Settings → Run Setup.")
        
        elif "grammar" in prompt_lower or "fix" in prompt_lower:
            return ("Here's how I would fix the grammar:\n\n"
                   "This is a demo response showing how Verdant would correct grammar. "
                   "In the full version, you would get actual AI-generated grammar corrections "
                   "for your specific text.\n\n"
                   "To get real AI responses, download the model using Settings → Run Setup.")
        
        elif "summarize" in prompt_lower:
            return ("Here's a summary:\n\n"
                   "This is a demo response showing how Verdant would summarize text. "
                   "In the full version, you would get an actual AI-generated summary "
                   "of your specific content.\n\n"
                   "To get real AI responses, download the model using Settings → Run Setup.")
        
        else:
            return ("Hello! I'm Verdant, your eco-conscious local AI assistant.\n\n"
                   "This is a demo response. To get real AI responses:\n"
                   "1. Go to Settings → Run Setup\n"
                   "2. Download the AI model (~3.8GB)\n"
                   "3. Start chatting with full AI capabilities!\n\n"
                   "🌿 100% local • 🔒 100% private • �� 95% less energy")


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

    def _apply_theme_setting(self):
        """Apply the selected theme setting"""
        theme = self.theme_var.get()
        if theme == "auto":
            theme = self._detect_system_theme()
        
        # In a real implementation, you would switch themes here
        # For now, we'll just update the status
        self._set_status(f"Theme set to {theme} mode")
        
        # You could implement actual theme switching here:
        # if theme == "light":
        #     self.root.style.theme_use("flatly")  # Light theme
        # else:
        #     self.root.style.theme_use("darkly")  # Dark theme

    def _export_all_data(self):
        """Export all user data for privacy control"""
        try:
            path = filedialog.asksaveasfilename(defaultextension=".zip", 
                                              filetypes=[("ZIP", "*.zip"), ("All Files", "*.*")], 
                                              title="Export all data")
            if not path:
                return
            
            # In a real implementation, you would create a comprehensive export
            # For now, we'll just export the chat history
            data = {
                "chat_history": self.chat_history,
                "preferences": self.prefs,
                "exported_at": __import__("time").time(),
                "version": "1.0"
            }
            
            # Save as JSON for now (in real app, create ZIP with multiple files)
            json_path = path.replace(".zip", ".json")
            Path(json_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
            self._set_status("Data exported successfully")
            
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
            self._set_status("Data export failed")

    def _clear_chat_history(self):
        """Clear all chat history for privacy"""
        if messagebox.askyesno("Clear History", 
                              "Are you sure you want to clear all chat history? This cannot be undone."):
            # Clear chat bubbles
            for row, _, _ in self.chat_bubbles:
                try:
                    row.destroy()
                except Exception:
                    pass
            self.chat_bubbles.clear()
            self.chat_history.clear()
            
            # Add system note
            self._add_system_note("Chat history cleared.")
            self._set_status("Chat history cleared")

    def _open_notification_settings(self):
        """Open notification settings dialog"""
        # In a real implementation, this would open a comprehensive notification settings dialog
        messagebox.showinfo("Notifications", 
                           "Notification settings would be configured here.\n\n"
                           "Features include:\n"
                           "• Sound notifications\n"
                           "• Desktop notifications\n"
                           "• Email summaries\n"
                           "• Do not disturb mode")


def main():
	root = tb.Window(themename="darkly")
	VerdantGUI(root)
	root.mainloop()


if __name__ == "__main__":
    main() 
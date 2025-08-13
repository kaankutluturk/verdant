#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from verdant import (
	UserPreferences,
	ModelDownloader,
	HardwareDetector,
	AIInference,
	PresetsManager,
	get_capabilities,
)

APP_TITLE = "Verdant"

BRAND = "#1DB954"
BG = "#0F1214"
FG = "#EAF2F6"
BUBBLE_USER = "#13181C"
BUBBLE_ASSIST = "#0E2518"

@dataclass
class GenParams:
	temperature: float
	top_p: float
	context: int
	n_gpu_layers: Optional[int]

class StreamWorker(QtCore.QObject):
	chunk = QtCore.Signal(str)
	finished = QtCore.Signal()
	error = QtCore.Signal(str)

	def __init__(self, ai: Optional[AIInference], prompt: str, is_demo: bool, parent=None):
		super().__init__(parent)
		self.ai = ai
		self.prompt = prompt
		self.is_demo = is_demo
		self._stop = False
		self._token_est = 0
		self._max_tokens = 256

	@QtCore.Slot()
	def run(self):
		try:
			if self.is_demo or self.ai is None:
				text = self._demo_response(self.prompt)
				for part in self._chunkify(text):
					if self._stop: break
					self._incr_tokens(part)
					self.chunk.emit(part)
					QtCore.QThread.msleep(60)
			else:
				for ch in self.ai.generate_response_stream(self.prompt):
					if self._stop: break
					self._incr_tokens(ch)
					self.chunk.emit(ch)
					if self._token_est >= self._max_tokens: break
			self.finished.emit()
		except Exception as e:
			self.error.emit(str(e))

	def stop(self):
		self._stop = True

	def _incr_tokens(self, s: str):
		self._token_est += max(0, len(s.split()))

	def _chunkify(self, s: str, n: int = 64):
		for i in range(0, len(s), n):
			yield s[i:i+n]

	def _demo_response(self, prompt: str) -> str:
		p = prompt.strip()
		low = p.lower()
		if "paraphrase" in low:
			return "Paraphrase: " + p.replace("paraphrase", "", 1).strip().capitalize()
		if "summarize" in low or "summary" in low:
			return "Summary: " + (p[:200] + ("…" if len(p)>200 else ""))
		if "fix" in low or "grammar" in low:
			return "Revised: " + p.replace(" there ", " they're ")
		return "Here are key points: • " + " • ".join([w for w in p.split()[:10]])

class Bubble(QtWidgets.QFrame):
	def __init__(self, text: str, sender: str, parent=None):
		super().__init__(parent)
		self.setObjectName("bubble")
		bg = BUBBLE_USER if sender=='user' else BUBBLE_ASSIST
		self.setStyleSheet(f"#bubble {{ background: {bg}; border-radius: 12px; }}")
		row = QtWidgets.QHBoxLayout(self)
		row.setContentsMargins(8, 8, 8, 8)
		row.setSpacing(8)
		avatar = QtWidgets.QLabel()
		avatar.setFixedSize(32,32)
		pm = QtGui.QPixmap(32,32); pm.fill(QtCore.Qt.transparent)
		p = QtGui.QPainter(pm); p.setRenderHint(QtGui.QPainter.Antialiasing)
		p.setBrush(QtGui.QColor(BRAND if sender=='assistant' else '#2a3339'))
		p.setPen(QtCore.Qt.NoPen); p.drawEllipse(0,0,32,32); p.end()
		avatar.setPixmap(pm)
		if sender=='assistant':
			row.addWidget(avatar)
		# Content container
		col = QtWidgets.QVBoxLayout(); col.setContentsMargins(0,0,0,0); col.setSpacing(4)
		toolbar = QtWidgets.QHBoxLayout(); toolbar.setContentsMargins(0,0,0,0)
		toolbar.addStretch(1)
		copy_btn = QtWidgets.QToolButton(); copy_btn.setText("⧉"); copy_btn.setToolTip("Copy")
		toolbar.addWidget(copy_btn)
		col.addLayout(toolbar)
		view = QtWidgets.QTextBrowser(); view.setOpenExternalLinks(True)
		view.setStyleSheet(f"background: {bg}; color: {FG}; border: 0;")
		html = self._to_html(text)
		view.setHtml(html)
		col.addWidget(view)
		row.addLayout(col, 1)
		if sender=='user':
			row.addWidget(avatar)
		copy_btn.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(view.toPlainText()))
		self.view = view

	def _to_html(self, text: str) -> str:
		if _md:
			try:
				h = _md.markdown(text, extensions=["fenced_code", "tables"])  # basic md
				return f"<div style='font-size:12pt; line-height:1.45'>{h}</div>"
			except Exception:
				pass
		# Fallback: escape minimal
		return "<pre style='white-space:pre-wrap; font-size:12pt;'>" + QtGui.QTextDocument().toHtmlEscaped(text) + "</pre>"

class ChatView(QtWidgets.QScrollArea):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWidgetResizable(True)
		self.viewport().setStyleSheet(f"background: {BG};")
		self.container = QtWidgets.QWidget()
		self.setWidget(self.container)
		self.v = QtWidgets.QVBoxLayout(self.container)
		self.v.setContentsMargins(12, 12, 12, 12)
		self.v.setSpacing(8)
		self.v.addStretch(1)

	def add_bubble(self, text: str, sender: str):
		row = QtWidgets.QHBoxLayout()
		row.setContentsMargins(0, 0, 0, 0)
		row.setSpacing(6)
		if sender == "user":
			row.addStretch(1)
			b = Bubble(text, sender)
			row.addWidget(b, 0)
		else:
			b = Bubble(text, sender)
			row.addWidget(b, 0)
			row.addStretch(1)
		self.v.insertLayout(self.v.count() - 1, row)
		QtCore.QTimer.singleShot(0, self._scroll_to_bottom)

	def _scroll_to_bottom(self):
		self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

class SettingsDialog(QtWidgets.QDialog):
	def __init__(self, prefs: dict, caps: dict, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Settings")
		self.setStyleSheet(f"background: {BG}; color: {FG};")
		self.prefs = prefs
		self.caps = caps
		self._build()

	def _build(self):
		v = QtWidgets.QVBoxLayout(self)
		form = QtWidgets.QFormLayout()
		self.temp = QtWidgets.QDoubleSpinBox()
		self.temp.setRange(0.0, 1.2)
		self.temp.setSingleStep(0.05)
		self.temp.setValue(float(self.prefs.get("temperature", 0.7) or 0.7))
		self.top_p = QtWidgets.QDoubleSpinBox()
		self.top_p.setRange(0.1, 1.0)
		self.top_p.setSingleStep(0.05)
		self.top_p.setValue(float(self.prefs.get("top_p", 0.9) or 0.9))
		self.ctx = QtWidgets.QSpinBox()
		self.ctx.setRange(256, int(self.caps.get("max_context", 2048) or 2048))
		self.ctx.setValue(int(self.prefs.get("context") or self.caps.get("max_context", 2048)))
		self.gpu_layers = QtWidgets.QSpinBox()
		self.gpu_layers.setRange(0, 64)
		self.gpu_layers.setValue(int(self.prefs.get("gpu_layers") or 0))
		self.instant_demo = QtWidgets.QCheckBox("Enable instant demo (no download)")
		self.instant_demo.setChecked(bool(self.prefs.get("instant_demo", True)))
		for lbl, w in (("Temperature", self.temp), ("Top-p", self.top_p), ("Context", self.ctx), ("GPU layers", self.gpu_layers)):
			form.addRow(lbl, w)
		v.addLayout(form)
		v.addWidget(self.instant_demo)
		btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
		btns.accepted.connect(self.accept)
		btns.rejected.connect(self.reject)
		v.addWidget(btns)

	def values(self) -> dict:
		return {
			"temperature": float(self.temp.value()),
			"top_p": float(self.top_p.value()),
			"context": int(self.ctx.value()),
			"gpu_layers": int(self.gpu_layers.value()),
			"instant_demo": bool(self.instant_demo.isChecked()),
		}

class TemplatesDialog(QtWidgets.QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Templates")
		self.setStyleSheet(f"background: {BG}; color: {FG};")
		self._build()
		self.selected: Optional[str] = None
		self.presets = PresetsManager.load_presets()
		self._populate()
	def _build(self):
		v = QtWidgets.QVBoxLayout(self)
		self.list = QtWidgets.QListWidget()
		self.list.currentItemChanged.connect(self._on_select)
		self.preview = QtWidgets.QPlainTextEdit(); self.preview.setReadOnly(True)
		self.preview.setStyleSheet(f"background: {BG}; color: {FG}; border: 1px solid #1a2228;")
		split = QtWidgets.QSplitter(); split.setOrientation(QtCore.Qt.Horizontal)
		split.addWidget(self.list); split.addWidget(self.preview)
		v.addWidget(split, 1)
		btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
		btns.accepted.connect(self._use)
		btns.rejected.connect(self.reject)
		v.addWidget(btns)
	def _populate(self):
		self.list.clear()
		for name in sorted(self.presets.keys()):
			self.list.addItem(name)
	def _on_select(self, cur, _prev):
		if not cur: return
		name = cur.text(); text = self.presets.get(name, "")
		self.preview.setPlainText(text)
		self.selected = name
	def _use(self):
		if not self.selected: return
		self.accept()

class CompareDialog(QtWidgets.QDialog):
	def __init__(self, caps: dict, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Compare Plans")
		self.setStyleSheet(f"background: {BG}; color: {FG};")
		v = QtWidgets.QVBoxLayout(self)
		lbl = QtWidgets.QLabel("Demo vs Premium")
		lbl.setStyleSheet("font-weight:600; font-size: 14pt;")
		v.addWidget(lbl)
		pts = QtWidgets.QTextBrowser(); pts.setStyleSheet(f"background:{BG}; color:{FG}; border:0;")
		pts.setHtml(
			f"""
			<ul>
			<li>Context: Demo up to {caps.get('max_context',2048)} • Premium up to 8K+</li>
			<li>Models: Demo 7B • Premium 13B/30B + specialized</li>
			<li>GPU: Optional layers • Premium tuned builds</li>
			<li>Tools: Demo basics • Premium RAG, batch, plugins</li>
			</ul>
			"""
		)
		v.addWidget(pts)
		btn = QtWidgets.QPushButton("Upgrade →")
		btn.setStyleSheet(f"background:{BRAND}; color:#0b100d; padding:10px 14px; border-radius:8px;")
		btn.clicked.connect(self._open)
		v.addWidget(btn, alignment=QtCore.Qt.AlignRight)
	def _open(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://kaankutluturk.github.io/verdant/"))
		self.accept()

class ModelManagerDialog(QtWidgets.QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Model Manager")
		self.setStyleSheet(f"background:{BG}; color:{FG};")
		self.downloader = ModelDownloader()
		self._build()
		self._refresh()
	def _build(self):
		v = QtWidgets.QVBoxLayout(self)
		self.table = QtWidgets.QTableWidget(0, 4)
		self.table.setHorizontalHeaderLabels(["Key","Name","Status","Size"])
		self.table.horizontalHeader().setStretchLastSection(True)
		v.addWidget(self.table)
		rowbtns = QtWidgets.QHBoxLayout()
		self.btn_dl = QtWidgets.QPushButton("Download")
		self.btn_del = QtWidgets.QPushButton("Delete")
		self.btn_open = QtWidgets.QPushButton("Open Folder")
		rowbtns.addWidget(self.btn_dl); rowbtns.addWidget(self.btn_del); rowbtns.addStretch(1); rowbtns.addWidget(self.btn_open)
		v.addLayout(rowbtns)
		self.btn_dl.clicked.connect(self._download)
		self.btn_del.clicked.connect(self._delete)
		self.btn_open.clicked.connect(self._open)
	def _refresh(self):
		from verdant import MODELS
		self.table.setRowCount(0)
		for key, m in MODELS.items():
			row = self.table.rowCount(); self.table.insertRow(row)
			self.table.setItem(row,0,QtWidgets.QTableWidgetItem(key))
			self.table.setItem(row,1,QtWidgets.QTableWidgetItem(m.name))
			mp = self.downloader.get_model_path(key)
			status = "Present" if mp else "Missing"
			size = f"{m.size_mb} MB"
			self.table.setItem(row,2,QtWidgets.QTableWidgetItem(status))
			self.table.setItem(row,3,QtWidgets.QTableWidgetItem(size))
	def _selected_key(self) -> Optional[str]:
		itm = self.table.item(self.table.currentRow(),0)
		return itm.text() if itm else None
	def _download(self):
		key = self._selected_key();
		if not key: return
		self.parent().status_label.setText("Downloading…")
		def task():
			ok = self.downloader.download_model(key)
			self.parent().status_label.setText("Download complete" if ok else "Download failed")
			self._refresh()
		QtCore.QTimer.singleShot(0, lambda: threading.Thread(target=task, daemon=True).start())
	def _delete(self):
		key = self._selected_key();
		if not key: return
		p = self.downloader.get_model_path(key)
		if p and p.exists():
			p.unlink(missing_ok=True)
		self._refresh()
	def _open(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.downloader.model_dir)))

class MainWindow(QtWidgets.QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle(APP_TITLE)
		self.resize(1080, 720)
		self.setStyleSheet(f"QMainWindow {{ background: {BG}; }}")
		self.caps = get_capabilities()
		self.prefs_path = None
		self.prefs = UserPreferences.load(self.prefs_path)
		self.model_key = self.prefs.get("model", "mistral-7b-q4")
		self.status = self.statusBar()
		self.status.setStyleSheet(f"color: {FG};")
		self.eco_saved_tokens = 0
		self._worker_thread = None
		self._worker = None
		self._toast = None
		# Initialize sessions dir before UI to avoid early access
		self._init_recent_sessions()
		self._build_ui()
		self._maybe_show_onboarding()

	def _build_ui(self):
		central = QtWidgets.QWidget(); self.setCentralWidget(central)
		root = QtWidgets.QVBoxLayout(central)
		# Header (unchanged below)
		header = QtWidgets.QHBoxLayout()
		self.status_label = QtWidgets.QLabel("Ready")
		self.status_label.setStyleSheet(f"color: {FG};")
		header.addWidget(self.status_label)
		self.eco_label = QtWidgets.QLabel("🌿 0.00 Wh")
		self.eco_label.setStyleSheet("color: %s; margin-left: 12px;" % BRAND)
		header.addWidget(self.eco_label)
		header.addStretch(1)
		btn_bench = QtWidgets.QToolButton(); btn_bench.setText("⚡")
		btn_bench.clicked.connect(self._on_bench)
		header.addWidget(btn_bench)
		self.btn_stop = QtWidgets.QToolButton(); self.btn_stop.setText("⏹")
		self.btn_stop.setEnabled(False)
		self.btn_stop.clicked.connect(self._on_stop)
		header.addWidget(self.btn_stop)
		btn_menu = QtWidgets.QToolButton(); btn_menu.setText("≡")
		btn_menu.setPopupMode(QtWidgets.QToolButton.InstantPopup)
		self._menu = QtWidgets.QMenu(self)
		self._menu.addAction("New chat", self._new_chat)
		self._menu.addAction("Save chat (JSON)", self._save_chat)
		self._menu.addAction("Load chat (JSON)", self._load_chat)
		self._recent_menu = self._menu.addMenu("Recent…")
		self._menu.addSeparator()
		self._menu.addAction("Export Markdown", self._export_markdown)
		self._menu.addAction("Export PDF", self._export_pdf)
		self._menu.addSeparator()
		self._menu.addAction("Templates", self._open_templates)
		self._menu.addAction("Model Manager", self._open_model_manager)
		self._menu.addAction("Compare plans", self._open_compare)
		btn_menu.setMenu(self._menu)
		header.addWidget(btn_menu)
		btn_settings = QtWidgets.QToolButton(); btn_settings.setText("⚙")
		btn_settings.clicked.connect(self._on_settings)
		header.addWidget(btn_settings)
		btn_upgrade = QtWidgets.QPushButton("★ Upgrade")
		btn_upgrade.setStyleSheet(f"background:{BRAND}; color:#0b100d; padding:6px 10px; border-radius:6px;")
		btn_upgrade.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://kaankutluturk.github.io/verdant/")))
		header.addWidget(btn_upgrade)
		root.addLayout(header)
		# Body split: sidebar + chat (replace sidebar with chat list)
		body = QtWidgets.QHBoxLayout()
		# Sidebar: Chat list and quick actions
		side = QtWidgets.QFrame(); side.setFixedWidth(260)
		side.setStyleSheet(f"background: #12171b; color:{FG}; border-right:1px solid #1a2228;")
		sv = QtWidgets.QVBoxLayout(side); sv.setContentsMargins(12,12,12,12); sv.setSpacing(8)
		new_btn = QtWidgets.QPushButton("⊕  New chat"); new_btn.clicked.connect(self._new_chat)
		sv.addWidget(new_btn)
		sv.addWidget(QtWidgets.QLabel("Chats"))
		self.chat_list = QtWidgets.QListWidget(); self.chat_list.itemActivated.connect(self._open_selected_chat)
		self.chat_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.chat_list.customContextMenuRequested.connect(self._chat_list_menu)
		sv.addWidget(self.chat_list, 1)
		# Footer actions
		act_row = QtWidgets.QHBoxLayout()
		act_row.addWidget(QtWidgets.QPushButton("Templates", clicked=self._open_templates))
		act_row.addWidget(QtWidgets.QPushButton("Models", clicked=self._open_model_manager))
		sv.addLayout(act_row)
		body.addWidget(side)
		# Chat + composer
		container = QtWidgets.QWidget(); cv = QtWidgets.QVBoxLayout(container)
		self.chat = ChatView(); cv.addWidget(self.chat, 1)
		self._add_hero()
		row = QtWidgets.QHBoxLayout()
		self.input = SendTextEdit(self); self.input.setPlaceholderText("Message Verdant…")
		self.input.setStyleSheet(f"background: {BG}; color: {FG}; border: 1px solid #1a2228; border-radius: 8px;")
		self.input.setFixedHeight(80)
		row.addWidget(self.input, 1)
		self.btn_send = QtWidgets.QPushButton("Send"); self.btn_send.clicked.connect(self._on_send)
		self.btn_send.setStyleSheet(f"QPushButton {{ background: {BRAND}; color: #0b100d; border-radius: 8px; padding: 10px 16px; }} QPushButton:hover {{ filter: brightness(1.05); }}")
		row.addWidget(self.btn_send, 0)
		cv.addLayout(row)
		body.addWidget(container, 1)
		root.addLayout(body, 1)
		self._rebuild_chat_list()

	def _add_hero(self):
		try:
			logo = Path(__file__).parent / "assets" / "logo" / "verdant-wordmark.svg"
			png = logo.with_suffix(".png")
			if logo.exists():
				try:
					import cairosvg
					if not png.exists():
						cairosvg.svg2png(url=str(logo), write_to=str(png), output_width=480)
				except Exception:
					pass
				if png.exists():
					pm = QtGui.QPixmap(str(png))
					lab = QtWidgets.QLabel()
					lab.setPixmap(pm)
					lab.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
					self.chat.v.insertWidget(0, lab)
		except Exception:
			pass

	def _maybe_show_onboarding(self):
		try:
			dl = ModelDownloader()
			if not dl.get_model_path(self.model_key) and not self.prefs.get("onboarded", False):
				ret = QtWidgets.QMessageBox.question(self, "Welcome", "Download the model now (~3.8GB)? You can also use Instant Demo.",
														   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
				if ret == QtWidgets.QMessageBox.Yes:
					self._run_setup_async()
				else:
					self.prefs["instant_demo"] = True
					UserPreferences.save(self.prefs, self.prefs_path)
				self.prefs["onboarded"] = True
				UserPreferences.save(self.prefs, self.prefs_path)
		except Exception:
			pass

	def _on_settings(self):
		d = SettingsDialog(self.prefs, self.caps, self)
		if d.exec() == QtWidgets.QDialog.Accepted:
			vals = d.values()
			self.prefs.update(vals)
			UserPreferences.save(self.prefs, self.prefs_path)
			self.status_label.setText("Preferences saved")

	def _on_bench(self):
		def task():
			try:
				dl = ModelDownloader(); mp = dl.get_model_path(self.model_key)
				if not mp:
					self.status_label.setText("Model not found — run setup or use demo")
					return
				ai = AIInference(mp, n_ctx=int(self.prefs.get("context") or self.caps.get("max_context", 2048)),
								temperature=float(self.prefs.get("temperature", 0.7) or 0.7),
								top_p=float(self.prefs.get("top_p", 0.9) or 0.9),
								n_gpu_layers_override=int(self.prefs.get("gpu_layers") or 0))
				from verdant import run_benchmark
				run_benchmark(ai, runs=1)
				self.status_label.setText("Benchmark complete")
			except Exception as e:
				self.status_label.setText(f"Benchmark error: {e}")
		QtCore.QTimer.singleShot(0, lambda: threading.Thread(target=task, daemon=True).start())

	def _on_send(self):
		if not self.input.toPlainText().strip(): return
		prompt = self.input.toPlainText().strip()
		self.input.clear()
		self.chat.add_bubble(prompt, sender="user")
		try:
			presets = PresetsManager.load_presets()
			preset_name = self.prefs.get("active_preset")
			if preset_name and preset_name in presets:
				prompt = f"{presets[preset_name]}\n\n{prompt}"
		except Exception:
			pass
		self._start_generation(prompt)

	def _on_stop(self):
		if self._worker:
			self._worker.stop()
			self.status_label.setText("Stopped")

	def _start_generation(self, prompt: str):
		self.status_label.setText("Generating…")
		self.btn_stop.setEnabled(True)
		self._append_assistant_holder()
		is_demo = bool(self.prefs.get("instant_demo", True))
		ai = None
		try:
			dl = ModelDownloader(); mp = dl.get_model_path(self.model_key)
			if mp and not is_demo:
				ai = AIInference(mp,
								n_ctx=int(self.prefs.get("context") or self.caps.get("max_context", 2048)),
								temperature=float(self.prefs.get("temperature", 0.7) or 0.7),
								top_p=float(self.prefs.get("top_p", 0.9) or 0.9),
								n_gpu_layers_override=int(self.prefs.get("gpu_layers") or 0))
		except Exception:
			ai = None
		self._run_stream(ai, prompt, is_demo or ai is None)

	def _append_assistant_holder(self):
		self.assist_row = QtWidgets.QHBoxLayout()
		self.assist_row.setContentsMargins(0, 0, 0, 0)
		self.assist_row.setSpacing(6)
		b = Bubble("", sender="assistant")
		self.assist_label = b.findChild(QtWidgets.QLabel)
		self.assist_row.addWidget(b, 0)
		self.assist_row.addStretch(1)
		self.chat.v.insertLayout(self.chat.v.count() - 1, self.assist_row)

	def _run_stream(self, ai: Optional[AIInference], prompt: str, is_demo: bool):
		self._worker_thread = QtCore.QThread(self)
		self._worker = StreamWorker(ai, prompt, is_demo)
		self._worker.moveToThread(self._worker_thread)
		self._worker_thread.started.connect(self._worker.run)
		self._worker.chunk.connect(self._on_chunk)
		self._worker.finished.connect(self._on_finish)
		self._worker.error.connect(self._on_error)
		self._worker_thread.start()

	@QtCore.Slot(str)
	def _on_chunk(self, ch: str):
		old = self.assist_label.text(); self.assist_label.setText(old + ch); self.chat._scroll_to_bottom()

	@QtCore.Slot()
	def _on_finish(self):
		self.status_label.setText("Done"); self.btn_stop.setEnabled(False)
		self._update_eco(estimate_tokens=len(self.assist_label.text().split()))
		if self._worker_thread:
			self._worker_thread.quit(); self._worker_thread.wait()

	@QtCore.Slot(str)
	def _on_error(self, err: str):
		self.status_label.setText(f"Error: {err}"); self.btn_stop.setEnabled(False)
		if self._worker_thread:
			self._worker_thread.quit(); self._worker_thread.wait()

	def _update_eco(self, estimate_tokens: int):
		try:
			self.eco_saved_tokens += max(1, int(estimate_tokens))
			saved_wh = self.eco_saved_tokens * 1e-4 * 0.95
			self.eco_label.setText(f"🌿 {saved_wh:.2f} Wh")
		except Exception:
			pass

	def _run_setup_async(self):
		self.status_label.setText("Setting up…")
		def task():
			try:
				dl = ModelDownloader()
				model = self.model_key or "mistral-7b-q4"
				if not HardwareDetector.check_requirements(model):
					self.status_label.setText("Requirements not met")
					return
				ok = dl.download_model(model)
				if not ok:
					self.status_label.setText("Download failed")
					return
				dl.validate_model(model)
				self.status_label.setText("Setup complete")
			except Exception as e:
				self.status_label.setText(f"Setup error: {e}")
		threading.Thread(target=task, daemon=True).start()

	def _init_recent_sessions(self):
		self.sessions_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Verdant" / "sessions"
		self.sessions_dir.mkdir(parents=True, exist_ok=True)

	def _rebuild_recent_menu(self):
		self._recent_menu.clear()
		items = sorted(self.sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
		for p in items:
			self._recent_menu.addAction(p.name, lambda pp=p: self._load_chat_path(pp))

	def _new_chat(self):
		self.chat = self.centralWidget().findChild(ChatView)
		self.chat.v = QtWidgets.QVBoxLayout(self.chat.container)
		self.chat.v.setContentsMargins(12,12,12,12)
		self.chat.v.setSpacing(8)
		self.chat.v.addStretch(1)
		self.status_label.setText("New chat started")
		self._rebuild_chat_list()

	def _save_chat(self):
		path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save chat", str(self.sessions_dir / "chat.json"), "JSON (*.json)")
		if not path: return
		data = {"history": self._history(), "saved_at": QtCore.QDateTime.currentDateTime().toSecsSinceEpoch(), "version": "1.0"}
		Path(path).write_text(__import__("json").dumps(data, indent=2), encoding="utf-8")
		self._rebuild_chat_list(); self.status_label.setText("Chat saved"); self._toast_msg("Saved")

	def _load_chat(self):
		path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load chat", str(self.sessions_dir), "JSON (*.json)")
		if path: self._load_chat_path(Path(path))
	def _load_chat_path(self, path: Path):
		try:
			data = __import__("json").loads(path.read_text(encoding="utf-8"))
			self._load_history(data.get("history", []))
			self.status_label.setText(f"Loaded {path.name}")
			self._toast_msg(f"Loaded {path.stem}")
		except Exception as e:
			self.status_label.setText(f"Load failed: {e}")

	def _history(self):
		# Extract chat bubbles to a list of role/content dicts
		hist = []
		for i in range(self.chat.v.count()-1):
			item = self.chat.v.itemAt(i)
			row = item.layout()
			if not row: continue
			w = row.itemAt(0).widget()
			if not isinstance(w, Bubble): continue
			label = w.findChild(QtWidgets.QLabel)
			role = "assistant" if w.styleSheet().find(BUBBLE_ASSIST) != -1 else "user"
			hist.append({"role": role, "content": label.text()})
		return hist
	def _load_history(self, hist):
		# Clear and rebuild
		self._new_chat()
		for msg in hist:
			self.chat.add_bubble(msg.get("content",""), sender=(msg.get("role") or "assistant"))

	def _export_markdown(self):
		path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Markdown", str(self.sessions_dir / "chat.md"), "Markdown (*.md)")
		if not path: return
		lines = []
		for i in range(self.chat.v.count()-1):
			row = self.chat.v.itemAt(i).layout();
			if not row: continue
			w = row.itemAt(0).widget();
			if not isinstance(w, Bubble): continue
			label = w.findChild(QtWidgets.QLabel)
			role = "assistant" if w.styleSheet().find(BUBBLE_ASSIST) != -1 else "user"
			lines.append(f"### {role.capitalize()}\n\n{label.text()}\n")
		Path(path).write_text("\n".join(lines), encoding="utf-8")
		self.status_label.setText("Exported Markdown")

	def _export_pdf(self):
		path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export PDF", str(self.sessions_dir / "chat.pdf"), "PDF (*.pdf)")
		if not path: return
		doc = QtGui.QTextDocument()
		html = ["<html><body style='background:#0F1214;color:#EAF2F6;font-family:Segoe UI;'>"]
		for i in range(self.chat.v.count()-1):
			row = self.chat.v.itemAt(i).layout();
			if not row: continue
			w = row.itemAt(0).widget();
			if not isinstance(w, Bubble): continue
			label = w.findChild(QtWidgets.QLabel)
			role = "assistant" if w.styleSheet().find(BUBBLE_ASSIST) != -1 else "user"
			html.append(f"<h3>{role.capitalize()}</h3><p>{QtGui.QTextDocument().toPlainText()}</p>")
			html[-1] = f"<h3>{role.capitalize()}</h3><p>{QtGui.QTextDocument().toHtmlEscaped(label.text()) if hasattr(QtGui.QTextDocument,'toHtmlEscaped') else label.text()}</p>"
		html.append("</body></html>")
		doc.setHtml("".join(html))
		printer = QtGui.QPdfWriter(path)
		printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.A4))
		doc.print_(printer)
		self.status_label.setText("Exported PDF")

	def _open_templates(self):
		d = TemplatesDialog(self)
		if d.exec() == QtWidgets.QDialog.Accepted and d.selected:
			self.prefs["active_preset"] = d.selected
			UserPreferences.save(self.prefs, self.prefs_path)
			self.status_label.setText(f"Selected template: {d.selected}")
	def _open_model_manager(self):
		ModelManagerDialog(self).exec()
	def _open_compare(self):
		CompareDialog(self.caps, self).exec()

	def _toast_msg(self, text: str):
		if self._toast: self._toast.close()
		self._toast = QtWidgets.QLabel(text, self)
		self._toast.setStyleSheet("background: rgba(20,20,20,200); color: #eaf2f6; padding: 8px 12px; border-radius: 8px;")
		self._toast.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.ToolTip)
		geo = self.geometry(); self._toast.move(geo.x()+geo.width()-280, geo.y()+geo.height()-120)
		self._toast.show(); QtCore.QTimer.singleShot(2000, self._toast.close)

	def _rebuild_chat_list(self):
		# Guard to ensure sessions_dir exists
		if not hasattr(self, "sessions_dir"):
			self._init_recent_sessions()
		self.chat_list.clear()
		items = sorted(self.sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]
		for p in items:
			itm = QtWidgets.QListWidgetItem(p.stem)
			itm.setData(QtCore.Qt.UserRole, p)
			self.chat_list.addItem(itm)

	def _open_selected_chat(self, item: QtWidgets.QListWidgetItem):
		p = item.data(QtCore.Qt.UserRole)
		if p: self._load_chat_path(p)

	def _chat_list_menu(self, pos):
		item = self.chat_list.itemAt(pos)
		if not item: return
		menu = QtWidgets.QMenu(self)
		menu.addAction("Rename", lambda: self._rename_chat_item(item))
		menu.addAction("Delete", lambda: self._delete_chat_item(item))
		menu.exec(self.chat_list.mapToGlobal(pos))

	def _rename_chat_item(self, item: QtWidgets.QListWidgetItem):
		p = item.data(QtCore.Qt.UserRole)
		name, ok = QtWidgets.QInputDialog.getText(self, "Rename chat", "Title:", text=item.text())
		if ok and name.strip():
			newp = p.with_name(name.strip()+".json")
			try:
				p.rename(newp)
			except Exception:
				pass
			self._rebuild_chat_list()

	def _delete_chat_item(self, item: QtWidgets.QListWidgetItem):
		p = item.data(QtCore.Qt.UserRole)
		try:
			p.unlink(missing_ok=True)
		except Exception:
			pass
		self._rebuild_chat_list()


class SendTextEdit(QtWidgets.QPlainTextEdit):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setTabChangesFocus(True)
	def keyPressEvent(self, e: QtGui.QKeyEvent):
		if e.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) and not (e.modifiers() & QtCore.Qt.ShiftModifier):
			# Parent MainWindow handles send
			p = self.parent()
			if hasattr(p, "_on_send"):
				p._on_send()
			return
		super().keyPressEvent(e)


def main():
	app = QtWidgets.QApplication(sys.argv)
	app.setApplicationDisplayName(APP_TITLE)
	app.setStyleSheet(f"QToolTip {{ background: #151a1e; color: {FG}; border: 0px; }}")
	w = MainWindow()
	w.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main() 
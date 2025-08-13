#!/usr/bin/env python3
import sys
import os
import traceback
import ctypes
from pathlib import Path

def _is_installed_app_dir(app_dir: Path) -> bool:
    try:
        # Consider installed if VerdantUpdater.exe exists or path is under Program Files
        if (app_dir / "VerdantUpdater.exe").exists():
            return True
        pf = os.environ.get("ProgramFiles", "")
        return str(app_dir).lower().startswith(str(pf).lower())
    except Exception:
        return False

def _log_startup_error(exc: BaseException) -> str:
    try:
        base_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.getcwd()), "Verdant", "logs")
        os.makedirs(base_dir, exist_ok=True)
        log_path = os.path.join(base_dir, "startup_error.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("Verdant startup error\n\n")
            f.write("Exception:\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            f.write("\nEnvironment:\n")
            for k in ("OS", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS", "USERNAME"):
                f.write(f"{k}={os.environ.get(k, '')}\n")
        return log_path
    except Exception:
        return ""

def _read_installed_version(app_dir: Path) -> str:
    try:
        v = (app_dir / "version.txt").read_text(encoding="utf-8").strip()
        return v if v else "v0.0.0"
    except Exception:
        return "v0.0.0"

def _fetch_latest_tag(timeout_sec: float = 6.0) -> str | None:
    try:
        import requests  # lazy import to avoid bundling issues if removed
        resp = requests.get(
            "https://api.github.com/repos/kaankutluturk/verdant/releases/latest",
            headers={"User-Agent": "VerdantApp/auto-update"},
            timeout=timeout_sec,
        )
        if resp.status_code == 200:
            data = resp.json()
            tag = data.get("tag_name")
            return str(tag) if tag else None
    except Exception:
        return None
    return None

def _launch_silent_updater(app_dir: Path) -> bool:
    try:
        # Instead of running an installer, prompt user to download latest EXE
        latest_url = "https://github.com/kaankutluturk/verdant/releases/latest/download/VerdantApp.exe"
        try:
            ctypes.windll.user32.MessageBoxW(
                None,
                f"A new version of Verdant is available.\n\nClick OK to open the download page.",
                "Verdant Update",
                0x40,
            )
        except Exception:
            pass
        import webbrowser
        webbrowser.open(latest_url)
        return True
    except Exception:
        return False

def _maybe_auto_update_on_launch() -> bool:
    # Returns True if an update was triggered (and app should exit)
    try:
        if "--no-update" in sys.argv or os.environ.get("VERDANT_NO_UPDATE") == "1":
            return False
        app_dir = Path(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)) if getattr(sys, "frozen", False) else os.getcwd())
        app_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(os.getcwd())
        if not _is_installed_app_dir(app_dir):
            return False
        installed = _read_installed_version(app_dir)
        latest = _fetch_latest_tag()
        if not latest or latest == installed:
            return False
        try:
            ctypes.windll.user32.MessageBoxW(None, f"Updating Verdant to {latest}. The app will close and restart.", "Verdant", 0x40)
        except Exception:
            pass
        if _launch_silent_updater(app_dir):
            return True
        return False
    except Exception:
        return False


def main():
    try:
        if _maybe_auto_update_on_launch():
            return 0
        if "--cli" in sys.argv:
            # Remove the flag and delegate to CLI
            sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a != "--cli"]
            from verdant import main as cli_main
            return cli_main()
        else:
            # Qt GUI only
            import verdant_qt as ui
            return ui.main()
    except Exception as exc:
        log_path = _log_startup_error(exc)
        # Best-effort user-visible error on Windows
        try:
            msg = f"Verdant failed to start.\n\n{exc}\n\nLog: {log_path or 'unavailable'}"
            ctypes.windll.user32.MessageBoxW(None, msg, "Verdant", 0x10)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main() 
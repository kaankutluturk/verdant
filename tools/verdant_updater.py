#!/usr/bin/env python3
import os
import sys
import json
import time
import tempfile
import subprocess
from pathlib import Path

import requests

OWNER = "kaankutluturk"
REPO = "verdant"
LATEST_API = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
LATEST_INSTALLER_URL = f"https://github.com/{OWNER}/{REPO}/releases/latest/download/verdant-setup.exe"
USER_AGENT = "VerdantUpdater/1.0 (+https://github.com/kaankutluturk/verdant)"


def log(message: str) -> None:
    try:
        base_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Verdant" / "logs"
        base_dir.mkdir(parents=True, exist_ok=True)
        with open(base_dir / "updater.log", "a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y-%m-%d %H:%M:%S] ") + message + "\n")
    except Exception:
        pass


def get_app_dir() -> Path:
    exe = Path(sys.executable)
    # Running as onefile EXE or via python
    if exe.suffix.lower() == ".exe":
        return exe.parent
    return Path.cwd()


def read_installed_version(app_dir: Path) -> str:
    try:
        version_path = app_dir / "version.txt"
        if version_path.exists():
            return version_path.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return "v0.0.0"


def get_latest_tag() -> str | None:
    try:
        r = requests.get(LATEST_API, headers={"User-Agent": USER_AGENT}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            tag = data.get("tag_name")
            return str(tag) if tag else None
        log(f"GitHub API status: {r.status_code}")
    except Exception as exc:
        log(f"Latest tag fetch error: {exc}")
    return None


def download_installer() -> Path | None:
    try:
        tmp = Path(tempfile.gettempdir()) / "verdant-setup-latest.exe"
        with requests.get(LATEST_INSTALLER_URL, headers={"User-Agent": USER_AGENT}, timeout=60, stream=True) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
        return tmp
    except Exception as exc:
        log(f"Download error: {exc}")
        return None


def run_installer_silent(installer_path: Path) -> None:
    try:
        args = [str(installer_path), "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES"]
        subprocess.Popen(args, close_fds=True)
        log("Launched installer silently")
    except Exception as exc:
        log(f"Launch installer error: {exc}")


def main() -> int:
    try:
        app_dir = get_app_dir()
        installed = read_installed_version(app_dir)
        latest = get_latest_tag()
        log(f"Installed={installed} Latest={latest}")
        if not latest or latest == installed:
            return 0
        inst = download_installer()
        if not inst:
            return 1
        run_installer_silent(inst)
        return 0
    except Exception as exc:
        log(f"Updater fatal error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 
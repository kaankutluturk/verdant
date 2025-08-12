#!/usr/bin/env python3
import sys
import os
import traceback

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


def main():
    try:
        if "--cli" in sys.argv:
            # Remove the flag and delegate to CLI
            sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a != "--cli"]
            from verdant import main as cli_main
            return cli_main()
        else:
            # Default to GUI
            import verdant_gui  # will run its own main
            return verdant_gui.main()
    except Exception as exc:
        log_path = _log_startup_error(exc)
        # Best-effort user-visible error on Windows
        try:
            import ctypes
            msg = f"Verdant failed to start.\n\n{exc}\n\nLog: {log_path or 'unavailable'}"
            ctypes.windll.user32.MessageBoxW(None, msg, "Verdant", 0x10)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main() 
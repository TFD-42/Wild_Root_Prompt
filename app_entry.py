#!/usr/bin/env python3
"""
Prompturgy — compiled app entry point.

This is the script build_app.py bundles into the standalone app via
PyInstaller. It mirrors Prompturgy.command's day-to-day launch behavior
(start Ollama if needed, launch the web UI, open the browser) in pure
Python so it works identically whether run from source or as a compiled
binary — no shell wrapper required.

Deliberately avoids any interactive install prompts: a windowed/onefile
compiled app has no console to type into, so if Ollama isn't installed at
all, this points the user to the download page and exits rather than
hanging on an input() call that can never be answered.
"""
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prompt_expert_enhance import is_ollama_installed, is_ollama_running, start_ollama_serve
from web_server import run_web_server


def main() -> int:
    print("Prompturgy starting...")

    if not is_ollama_installed():
        print("Ollama is not installed. Opening the download page — "
              "install it, then relaunch Prompturgy.")
        try:
            webbrowser.open("https://ollama.com/download")
        except Exception:
            pass
        return 1

    if not is_ollama_running():
        print("Ollama is not running — starting it...")
        start_ollama_serve()

    run_web_server(port=7860, open_browser=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

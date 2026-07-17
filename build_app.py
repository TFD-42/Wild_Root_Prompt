#!/usr/bin/env python3
"""
Wild_Root_Prompt — build a standalone, single-icon compiled app.

Bundles app_entry.py (which launches the web UI) into one platform-native
executable via PyInstaller:
  macOS   -> dist/Wild_Root_Prompt.app   (double-click, custom icon)
  Windows -> dist/Wild_Root_Prompt.exe   (double-click, custom icon)
  Linux   -> dist/Wild_Root_Prompt       (single binary; run from a terminal or
                                     wire up a .desktop file for a menu icon)

Usage:
    python3 build_app.py

Requires: pip install pyinstaller  (already listed in requirements-build.txt)
"""
import platform
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
ENTRY_SCRIPT = BASE_DIR / "app_entry.py"
APP_NAME = "Wild_Root_Prompt"

DATA_FILES = ["prompt_expert_methodology.json", "prompt_templates.json"]


def _check_pyinstaller() -> bool:
    try:
        import PyInstaller  # noqa: F401
        return True
    except ImportError:
        return False


def _data_arg(filename: str, sep: str) -> str:
    return f"--add-data={filename}{sep}."


def build() -> int:
    system = platform.system()

    if not _check_pyinstaller():
        print("[!] PyInstaller is not installed. Run: pip install pyinstaller")
        return 1

    for f in DATA_FILES:
        if not (BASE_DIR / f).exists():
            print(f"[!] Missing required data file: {f}")
            return 1

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        f"--name={APP_NAME}",
    ]

    if system == "Darwin":
        # --onefile + --windowed is deprecated for macOS .app bundles (a .app
        # can't be a single file) and PyInstaller will make it a hard error
        # in v7. --onedir (the default when --onefile is omitted) is what
        # actually produces a proper double-clickable .app bundle.
        icon = ASSETS_DIR / "icon.icns"
        sep = ":"
        args += ["--windowed"]
        if icon.exists():
            args += [f"--icon={icon}"]
    elif system == "Windows":
        icon = ASSETS_DIR / "icon.ico"
        sep = ";"
        args += ["--onefile", "--windowed"]
        if icon.exists():
            args += [f"--icon={icon}"]
    else:
        # Linux: no native single-icon bundle format from PyInstaller alone;
        # produce a plain onefile binary. See README for .desktop file setup.
        sep = ":"
        args += ["--onefile"]

    for f in DATA_FILES:
        args.append(_data_arg(f, sep))

    args.append(str(ENTRY_SCRIPT))

    print(f"Building for {system}...")
    print(" ".join(args))
    result = subprocess.run(args, cwd=BASE_DIR)
    if result.returncode != 0:
        print("[!] Build failed.")
        return result.returncode

    dist_dir = BASE_DIR / "dist"
    if system == "Darwin":
        out_path = dist_dir / f"{APP_NAME}.app"
    elif system == "Windows":
        out_path = dist_dir / f"{APP_NAME}.exe"
    else:
        out_path = dist_dir / APP_NAME

    print()
    if out_path.exists():
        print(f"Build complete: {out_path}")
        if system == "Darwin":
            print(f"Double-click {out_path.name} in Finder, or drag it to /Applications.")
        elif system == "Windows":
            print(f"Double-click {out_path.name} in Explorer.")
        else:
            print(f"Run it with: {out_path}")
    else:
        print("[!] Build finished but the expected output was not found — check the PyInstaller log above.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(build())

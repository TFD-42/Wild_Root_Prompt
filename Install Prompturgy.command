#!/usr/bin/env bash
# Double-click entry point for macOS — runs the full installer in Terminal.
# (Equivalent one-line terminal command: bash install.sh)
cd "$(dirname "$0")"
chmod +x install.sh
./install.sh
echo
read -p "Press Enter to close this window..." _

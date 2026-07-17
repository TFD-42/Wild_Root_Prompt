#!/usr/bin/env bash
# Wild_Root_Prompt — macOS Finder double-click launcher
# Opens the web UI at http://localhost:7860

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if present
if [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
elif ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 not found. Run install.sh first."
    read -p "Press ENTER to close..." _
    exit 1
fi

# Start Ollama if not running
if ! curl -s "http://localhost:11434/api/tags" &>/dev/null; then
    echo "  Starting Ollama..."
    open -a Ollama 2>/dev/null || ollama serve &>/dev/null &
    sleep 3
fi

echo ""
echo "  Wild_Root_Prompt — Starting web UI..."
echo "  URL: http://localhost:7860"
echo "  Press Ctrl+C to stop."
echo ""

exec python3 prompt_expert_enhance.py --web

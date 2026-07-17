#!/usr/bin/env bash
# ============================================================
#  Prompturgy Installer — Android / Termux
#  Dedicated installer for Termux environment
#  (Ollama not available on Android — configure remote server)
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAIN_SCRIPT="$SCRIPT_DIR/prompt_expert_enhance.py"
LAUNCHER="$SCRIPT_DIR/Prompturgy"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $1"; }

echo ""
echo "============================================================"
echo "   Prompturgy  —  Termux / Android Installer"
echo "============================================================"
echo ""
warn "Ollama does not run on Android/Termux."
echo "  You need a remote Ollama server on your PC or a LAN server."
echo "  After installation, set the Ollama URL in Prompturgy:"
echo "    Menu 8 > Ollama URL > http://<server-ip>:11434/api/generate"
echo ""
read -p "  Continue? [y/N] > " CONT
[ "${CONT,,}" != "y" ] && { echo "  Aborted."; exit 0; }

# --------------------------------------------------------------
# 1. Update Termux packages
# --------------------------------------------------------------
echo ""
info "Updating package list..."
pkg update -y && pkg upgrade -y
sleep 1
ok "Packages updated."

# --------------------------------------------------------------
# 2. Install Python
# --------------------------------------------------------------
echo ""
info "Installing Python..."
pkg install python -y
sleep 1
ok "Python installed: $(python3 --version)"

# --------------------------------------------------------------
# 3. Install pip dependencies
# --------------------------------------------------------------
echo ""
info "Installing pip dependencies (requests, flask)..."
pip install --upgrade pip -q
sleep 1
pip install requests flask -q
sleep 1
ok "Dependencies installed."

# --------------------------------------------------------------
# 4. Storage permission (needed to access outputs/)
# --------------------------------------------------------------
echo ""
info "Requesting storage access (for outputs/ folder)..."
termux-setup-storage 2>/dev/null || warn "Storage setup skipped (termux-setup-storage not found)"
sleep 1

# --------------------------------------------------------------
# 5. Create launcher
# --------------------------------------------------------------
echo ""
info "Creating launcher..."

cat > "$LAUNCHER" << 'LAUNCH'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  Prompturgy — Termux Mode"
echo "  ─────────────────────────"
echo "  Note: Ollama must be running on a remote machine."
echo "  Configure URL in menu 8 > Advanced settings."
echo ""
echo "  1. Web UI  (visit http://localhost:7860 in browser)"
echo "  2. CLI interactive"
echo "  3. CLI with remote Ollama URL"
echo ""
read -p "  Choice [2] > " CHOICE
CHOICE=${CHOICE:-2}

case "$CHOICE" in
  1) python3 prompt_expert_enhance.py web --no-browser
     echo "  Open: http://localhost:7860" ;;
  3) read -p "  Ollama URL [http://192.168.1.x:11434/api/generate] > " OURL
     OURL=${OURL:-"http://localhost:11434/api/generate"}
     python3 prompt_expert_enhance.py generate "test" --ollama-url "$OURL" ;;
  *) python3 prompt_expert_enhance.py ;;
esac
LAUNCH

chmod +x "$LAUNCHER"
ok "Launcher created: $LAUNCHER"

# --------------------------------------------------------------
# 6. Done
# --------------------------------------------------------------
echo ""
echo "============================================================"
echo -e "${GREEN}   Installation complete!${NC}"
echo "============================================================"
echo ""
echo "  Launch:"
echo -e "  ${CYAN}$LAUNCHER${NC}"
echo ""
echo "  Or directly:"
echo -e "  ${CYAN}cd \"$SCRIPT_DIR\" && python3 prompt_expert_enhance.py${NC}"
echo ""
echo "  Important — connect to your Ollama server:"
echo "  1. Start Ollama on your PC"
echo "  2. Allow LAN connections: OLLAMA_HOST=0.0.0.0 ollama serve"
echo "  3. In Prompturgy menu 8, set Ollama URL to:"
echo "     http://<your-pc-ip>:11434/api/generate"
echo ""

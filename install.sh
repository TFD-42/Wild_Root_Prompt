#!/usr/bin/env bash
# ============================================================
#  Prompturgy Installer — macOS / Linux
#  Installs Ollama, Python 3, creates venv, installs deps,
#  creates Prompturgy launcher
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
MAIN_SCRIPT="$SCRIPT_DIR/prompt_expert_enhance.py"
LAUNCHER="$SCRIPT_DIR/Prompturgy"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $1"; }
step()  { echo -e "\n${BOLD}$1${NC}"; }

echo ""
echo "============================================================"
echo "   Prompturgy  —  Automatic Installation"
echo "   macOS / Linux"
echo "============================================================"
echo ""

# --------------------------------------------------------------
# 1. Detect OS
# --------------------------------------------------------------
step "1/7  Detecting system"
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
    Darwin) OS_LABEL="macOS" ;;
    Linux)
        # Detect Termux (Android)
        if [ -d "/data/data/com.termux" ] || [ -n "$TERMUX_VERSION" ]; then
            OS_LABEL="Termux (Android)"
        else
            OS_LABEL="Linux"
        fi
        ;;
    *)      OS_LABEL="$OS" ;;
esac
info "OS: $OS_LABEL  |  Arch: $ARCH"

# --------------------------------------------------------------
# 2. Ollama
# --------------------------------------------------------------
step "2/7  Checking Ollama"
if command -v ollama &>/dev/null; then
    ok "Ollama already installed: $(command -v ollama)"
    # Start daemon if not running
    if ! curl -s "http://localhost:11434/api/tags" &>/dev/null; then
        info "Starting Ollama service..."
        if [ "$OS" = "Darwin" ]; then
            open -a Ollama 2>/dev/null || ollama serve &>/dev/null &
        else
            ollama serve &>/dev/null &
        fi
        sleep 3
    fi
else
    info "Ollama not found. Installing..."
    if [ "$OS_LABEL" = "Termux (Android)" ]; then
        warn "Ollama is not available for Termux/Android."
        warn "You can use a remote Ollama server. Configure the URL in Prompturgy settings."
        warn "Continuing installation without Ollama..."
    elif [ "$OS" = "Darwin" ] || [ "$OS" = "Linux" ]; then
        curl -fsSL https://ollama.com/install.sh | sh
        sleep 2
        if command -v ollama &>/dev/null; then
            ok "Ollama installed."
            # Start daemon
            if [ "$OS" = "Darwin" ]; then
                open -a Ollama 2>/dev/null || ollama serve &>/dev/null &
            else
                ollama serve &>/dev/null &
            fi
            sleep 3
        else
            fail "Ollama installation failed. Install manually: https://ollama.com/download"
        fi
    fi
fi

# --------------------------------------------------------------
# 3. Python 3
# --------------------------------------------------------------
step "3/7  Checking Python 3"
PYTHON_CMD=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        PY_VER="$("$candidate" --version 2>&1)"
        PY_MAJOR="$("$candidate" -c 'import sys; print(sys.version_info.major)' 2>/dev/null || echo 0)"
        PY_MINOR="$("$candidate" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo 0)"
        if [ "$PY_MAJOR" = "3" ] && [ "$PY_MINOR" -ge 8 ]; then
            PYTHON_CMD="$candidate"
            break
        fi
    fi
done

if [ -n "$PYTHON_CMD" ]; then
    ok "Python 3 found: $PYTHON_CMD ($PY_VER)"
else
    info "Python 3.8+ not found. Installing..."
    if [ "$OS_LABEL" = "Termux (Android)" ]; then
        pkg install python -y
    elif [ "$OS" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            brew install python3
        else
            warn "Installing Homebrew first..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv 2>/dev/null)"
            brew install python3
        fi
    elif [ "$OS" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -y && sudo apt-get install -y python3 python3-pip python3-venv
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3 python3-pip
        elif command -v pacman &>/dev/null; then
            sudo pacman -Sy --noconfirm python python-pip
        elif command -v apk &>/dev/null; then
            sudo apk add python3 py3-pip
        fi
    fi
    sleep 2
    for candidate in python3 python; do
        if command -v "$candidate" &>/dev/null; then
            PY_MAJOR="$("$candidate" -c 'import sys; print(sys.version_info.major)' 2>/dev/null || echo 0)"
            if [ "$PY_MAJOR" = "3" ]; then
                PYTHON_CMD="$candidate"
                break
            fi
        fi
    done
    if [ -n "$PYTHON_CMD" ]; then
        ok "Python 3 installed: $PYTHON_CMD"
    else
        fail "Could not install Python 3. Please install manually."
        exit 1
    fi
fi

# --------------------------------------------------------------
# 4. venv
# --------------------------------------------------------------
step "4/7  Creating virtual environment"

# Termux: no venv module needed, use pip directly
IS_TERMUX=false
[ "$OS_LABEL" = "Termux (Android)" ] && IS_TERMUX=true

if [ "$IS_TERMUX" = true ]; then
    ok "Termux: using global pip (no venv)"
    PYTHON_CMD="${PYTHON_CMD:-python3}"
else
    if [ -d "$VENV_DIR" ]; then
        ok "Existing venv: $VENV_DIR"
    else
        info "Creating venv..."
        "$PYTHON_CMD" -m venv "$VENV_DIR" 2>/dev/null || {
            warn "venv creation failed, trying to install python3-venv..."
            if command -v apt-get &>/dev/null; then
                sudo apt-get install -y python3-venv
            fi
            "$PYTHON_CMD" -m venv "$VENV_DIR"
        }
        # Give venv time to fully initialize (slow on some systems)
        sleep 2
        ok "venv created: $VENV_DIR"
    fi

    info "Activating venv..."
    source "$VENV_DIR/bin/activate"
    # Wait for activation to settle
    sleep 1
    ok "venv active: $(which python3)"
fi

# --------------------------------------------------------------
# 5. pip + dependencies
# --------------------------------------------------------------
step "5/7  Installing dependencies"

# Upgrade pip first (important — old pip fails on some packages)
info "Upgrading pip..."
if [ "$IS_TERMUX" = true ]; then
    pip install --upgrade pip -q
else
    "$VENV_DIR/bin/pip" install --upgrade pip -q
fi
sleep 1
ok "pip up to date."

if [ -f "$REQ_FILE" ]; then
    info "Installing from requirements.txt..."
    if [ "$IS_TERMUX" = true ]; then
        pip install -r "$REQ_FILE" -q
    else
        "$VENV_DIR/bin/pip" install -r "$REQ_FILE" -q
    fi
    sleep 1
    ok "Dependencies installed (requests, flask)."
else
    warn "requirements.txt not found — installing manually."
    if [ "$IS_TERMUX" = true ]; then
        pip install requests flask -q
    else
        "$VENV_DIR/bin/pip" install requests flask -q
    fi
    ok "requests + flask installed."
fi

# --------------------------------------------------------------
# 6. Create Prompturgy launcher
# --------------------------------------------------------------
step "6/7  Creating launcher"

if [ "$IS_TERMUX" = true ]; then
    # Termux: simple script, no venv
    cat > "$LAUNCHER" << LAUNCHER_SCRIPT
#!/usr/bin/env bash
cd "$SCRIPT_DIR"
echo ""
echo "  Starting Prompturgy..."
echo "  Web UI: http://localhost:7860"
echo "  CLI   : python3 prompt_expert_enhance.py"
echo ""
echo "  Choose mode:"
echo "    1. Web UI  (open browser / curl)"
echo "    2. CLI interactive"
echo ""
read -p "  Choice [1] > " CHOICE
CHOICE=\${CHOICE:-1}
if [ "\$CHOICE" = "1" ]; then
    python3 prompt_expert_enhance.py web --no-browser
else
    python3 prompt_expert_enhance.py
fi
LAUNCHER_SCRIPT
else
    # macOS / Linux: full launcher with venv + browser
    cat > "$LAUNCHER" << LAUNCHER_SCRIPT
#!/usr/bin/env bash
cd "$SCRIPT_DIR"
source ".venv/bin/activate"

# Start Ollama if not running
if ! curl -s "http://localhost:11434/api/tags" &>/dev/null; then
    if [ "\$(uname)" = "Darwin" ]; then
        open -a Ollama 2>/dev/null || ollama serve &>/dev/null &
    else
        ollama serve &>/dev/null &
    fi
    sleep 2
fi

exec python3 prompt_expert_enhance.py --web "\$@"
LAUNCHER_SCRIPT
fi

chmod +x "$LAUNCHER"
ok "Launcher created: $LAUNCHER"

# macOS: also create a .command file for Finder double-click
if [ "$OS" = "Darwin" ]; then
    COMMAND_LAUNCHER="$SCRIPT_DIR/Prompturgy.command"
    cat > "$COMMAND_LAUNCHER" << 'COMMAND_SCRIPT'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
source ".venv/bin/activate"
if ! curl -s "http://localhost:11434/api/tags" &>/dev/null; then
    open -a Ollama 2>/dev/null || ollama serve &>/dev/null &
    sleep 2
fi
python3 prompt_expert_enhance.py --web
COMMAND_SCRIPT
    chmod +x "$COMMAND_LAUNCHER"
    ok "macOS Finder launcher: Prompturgy.command (double-click to open)"
fi

# --------------------------------------------------------------
# 7. Done
# --------------------------------------------------------------
step "7/7  Installation complete"
echo ""
echo "============================================================"
echo -e "${GREEN}   Installation complete!${NC}"
echo "============================================================"
echo ""
if [ "$IS_TERMUX" = true ]; then
    echo "  Launch Prompturgy:"
    echo -e "  ${CYAN}$LAUNCHER${NC}"
    echo ""
    echo "  Or directly:"
    echo -e "  ${CYAN}cd \"$SCRIPT_DIR\" && python3 prompt_expert_enhance.py${NC}"
elif [ "$OS" = "Darwin" ]; then
    echo "  Launch options:"
    echo ""
    echo -e "  ${CYAN}Double-click:  Prompturgy.command${NC}   ← opens web UI in browser"
    echo -e "  ${CYAN}Terminal:      ./Prompturgy${NC}          ← same, from terminal"
    echo -e "  ${CYAN}CLI only:      source .venv/bin/activate && python3 prompt_expert_enhance.py${NC}"
else
    echo "  Launch options:"
    echo ""
    echo -e "  ${CYAN}./Prompturgy${NC}    ← opens web UI in browser"
    echo -e "  ${CYAN}source .venv/bin/activate && python3 prompt_expert_enhance.py${NC}  ← CLI"
fi
echo ""

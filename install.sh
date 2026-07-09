#!/usr/bin/env bash
# ============================================================
#  Pro-Prompt Installer — macOS / Linux
#  Installs Ollama, Python 3, creates venv, installs deps
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
MAIN_SCRIPT="$SCRIPT_DIR/prompt_expert_enhance.py"

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
echo "   Pro-Prompt  —  Automatic Installation"
echo "============================================================"
echo ""

# --------------------------------------------------------------
# 1. Detect OS
# --------------------------------------------------------------
OS="$(uname -s)"
case "$OS" in
    Darwin) OS_LABEL="macOS" ;;
    Linux)  OS_LABEL="Linux" ;;
    *)      OS_LABEL="$OS"   ;;
esac
info "Detected OS: $OS_LABEL"

# --------------------------------------------------------------
# 2. Ollama
# --------------------------------------------------------------
if command -v ollama &>/dev/null; then
    ok "Ollama already installed: $(command -v ollama)"
else
    info "Ollama not found. Installing..."
    if [ "$OS" = "Darwin" ] || [ "$OS" = "Linux" ]; then
        curl -fsSL https://ollama.com/install.sh | sh
        sleep 2
        if command -v ollama &>/dev/null; then
            ok "Ollama installed successfully."
        else
            fail "Ollama installation failed."
            echo "     Install manually: https://ollama.com/download"
        fi
    else
        warn "OS not supported for automatic Ollama install."
        echo "     Install manually: https://ollama.com/download"
    fi
fi

# --------------------------------------------------------------
# 3. Python 3
# --------------------------------------------------------------
PYTHON_CMD=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        PY_VER="$("$candidate" --version 2>&1)"
        PY_MAJOR="$("$candidate" -c 'import sys; print(sys.version_info.major)' 2>/dev/null || echo 0)"
        if [ "$PY_MAJOR" = "3" ]; then
            PYTHON_CMD="$candidate"
            break
        fi
    fi
done

if [ -n "$PYTHON_CMD" ]; then
    ok "Python 3 found: $PYTHON_CMD ($PY_VER)"
else
    info "Python 3 not found. Installing..."
    if [ "$OS" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            brew install python3
        else
            warn "Homebrew not installed. Installing Homebrew first..."
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
        else
            fail "Package manager not recognized."
            echo "     Install Python 3 manually."
            exit 1
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
        fail "Could not install Python 3."
        exit 1
    fi
fi

# --------------------------------------------------------------
# 4. pip
# --------------------------------------------------------------
if "$PYTHON_CMD" -m pip --version &>/dev/null; then
    ok "pip available."
else
    info "pip not found. Installing..."
    if [ "$OS" = "Darwin" ]; then
        "$PYTHON_CMD" -m ensurepip --upgrade 2>/dev/null || brew install python3
    elif [ "$OS" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y python3-pip
        else
            "$PYTHON_CMD" -m ensurepip --upgrade 2>/dev/null || curl -fsSL https://bootstrap.pypa.io/get-pip.py | "$PYTHON_CMD"
        fi
    fi
    sleep 1
    if "$PYTHON_CMD" -m pip --version &>/dev/null; then
        ok "pip installed."
    else
        fail "Could not install pip."
        exit 1
    fi
fi

# --------------------------------------------------------------
# 5. venv
# --------------------------------------------------------------
if [ -d "$VENV_DIR" ]; then
    ok "Existing venv detected: $VENV_DIR"
else
    info "Creating virtual environment..."
    "$PYTHON_CMD" -m venv "$VENV_DIR" 2>/dev/null
    if [ $? -ne 0 ]; then
        warn "python3-venv missing, installing..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y python3-venv
        fi
        "$PYTHON_CMD" -m venv "$VENV_DIR"
    fi
    sleep 2
    ok "venv created: $VENV_DIR"
fi

info "Activating venv..."
source "$VENV_DIR/bin/activate"
sleep 1
ok "venv active: $(which python3)"

# --------------------------------------------------------------
# 6. Install dependencies
# --------------------------------------------------------------
if [ -f "$REQ_FILE" ]; then
    info "Installing dependencies..."
    pip install --upgrade pip -q
    pip install -r "$REQ_FILE" -q
    sleep 1
    ok "Dependencies installed."
else
    warn "requirements.txt not found — skipping."
fi

# --------------------------------------------------------------
# 7. Done
# --------------------------------------------------------------
echo ""
echo "============================================================"
echo -e "${GREEN}   Installation complete!${NC}"
echo "============================================================"
echo ""
echo "  To launch Pro-Prompt:"
echo ""
echo -e "  ${CYAN}cd \"$SCRIPT_DIR\"${NC}"
echo -e "  ${CYAN}source .venv/bin/activate${NC}"
echo -e "  ${CYAN}python3 prompt_expert_enhance.py${NC}"
echo ""
echo "  One-liner:"
echo ""
echo -e "  ${CYAN}cd \"$SCRIPT_DIR\" && source .venv/bin/activate && python3 prompt_expert_enhance.py${NC}"
echo ""

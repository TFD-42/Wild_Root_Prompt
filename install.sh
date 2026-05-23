#!/usr/bin/env bash
# ============================================================
#  Pro-Prompt Installer — macOS / Linux
#  Installs Ollama, Python 3, creates venv, installs deps
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
MAIN_SCRIPT="$SCRIPT_DIR/prompt_expert_enhence.py"

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
echo "   Pro-Prompt  —  Installation automatique"
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
info "OS detecte : $OS_LABEL"

# --------------------------------------------------------------
# 2. Ollama
# --------------------------------------------------------------
if command -v ollama &>/dev/null; then
    ok "Ollama deja installe : $(command -v ollama)"
else
    info "Ollama non trouve. Installation en cours ..."
    if [ "$OS" = "Darwin" ] || [ "$OS" = "Linux" ]; then
        curl -fsSL https://ollama.com/install.sh | sh
        sleep 2
        if command -v ollama &>/dev/null; then
            ok "Ollama installe avec succes."
        else
            fail "Installation Ollama echouee."
            echo "     Installe manuellement : https://ollama.com/download"
        fi
    else
        warn "OS non supporte pour install automatique Ollama."
        echo "     Installe manuellement : https://ollama.com/download"
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
    ok "Python 3 trouve : $PYTHON_CMD ($PY_VER)"
else
    info "Python 3 non trouve. Installation en cours ..."
    if [ "$OS" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            brew install python3
        else
            warn "Homebrew non installe. Installation de Homebrew d'abord ..."
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
            fail "Gestionnaire de paquets non reconnu."
            echo "     Installe Python 3 manuellement."
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
        ok "Python 3 installe : $PYTHON_CMD"
    else
        fail "Impossible d'installer Python 3."
        exit 1
    fi
fi

# --------------------------------------------------------------
# 4. pip
# --------------------------------------------------------------
if "$PYTHON_CMD" -m pip --version &>/dev/null; then
    ok "pip disponible."
else
    info "pip non trouve. Installation ..."
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
        ok "pip installe."
    else
        fail "Impossible d'installer pip."
        exit 1
    fi
fi

# --------------------------------------------------------------
# 5. venv
# --------------------------------------------------------------
if [ -d "$VENV_DIR" ]; then
    ok "venv existant detecte : $VENV_DIR"
else
    info "Creation du venv ..."
    "$PYTHON_CMD" -m venv "$VENV_DIR" 2>/dev/null
    if [ $? -ne 0 ]; then
        warn "python3-venv manquant, installation ..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y python3-venv
        fi
        "$PYTHON_CMD" -m venv "$VENV_DIR"
    fi
    sleep 2
    ok "venv cree : $VENV_DIR"
fi

info "Activation du venv ..."
source "$VENV_DIR/bin/activate"
sleep 1
ok "venv actif : $(which python3)"

# --------------------------------------------------------------
# 6. Install dependencies
# --------------------------------------------------------------
if [ -f "$REQ_FILE" ]; then
    info "Installation des dependances ..."
    pip install --upgrade pip -q
    pip install -r "$REQ_FILE" -q
    sleep 1
    ok "Dependances installees."
else
    warn "requirements.txt non trouve — skip."
fi

# --------------------------------------------------------------
# 7. Done
# --------------------------------------------------------------
echo ""
echo "============================================================"
echo -e "${GREEN}   Installation terminee !${NC}"
echo "============================================================"
echo ""
echo "  Pour lancer Pro-Prompt :"
echo ""
echo -e "  ${CYAN}cd \"$SCRIPT_DIR\"${NC}"
echo -e "  ${CYAN}source .venv/bin/activate${NC}"
echo -e "  ${CYAN}python3 prompt_expert_enhence.py${NC}"
echo ""
echo "  (ou en une ligne) :"
echo ""
echo -e "  ${CYAN}cd \"$SCRIPT_DIR\" && source .venv/bin/activate && python3 prompt_expert_enhence.py${NC}"
echo ""

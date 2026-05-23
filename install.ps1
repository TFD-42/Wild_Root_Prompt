# ============================================================
#  Pro-Prompt Installer — Windows (PowerShell)
#  Installs Ollama, Python 3, creates venv, installs deps
# ============================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir   = Join-Path $ScriptDir ".venv"
$ReqFile   = Join-Path $ScriptDir "requirements.txt"
$MainScript = Join-Path $ScriptDir "prompt_expert_enhence.py"

function Info($msg)  { Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Ok($msg)    { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Warn($msg)  { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Fail($msg)  { Write-Host "[FAIL]  $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "============================================================"
Write-Host "   Pro-Prompt  -  Installation automatique (Windows)"
Write-Host "============================================================"
Write-Host ""

# --------------------------------------------------------------
# 1. Ollama
# --------------------------------------------------------------
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaPath) {
    Ok "Ollama deja installe : $($ollamaPath.Source)"
} else {
    Info "Ollama non trouve. Installation en cours ..."

    $installed = $false

    # Tentative winget
    $wingetPath = Get-Command winget -ErrorAction SilentlyContinue
    if ($wingetPath) {
        try {
            Info "Installation via winget ..."
            winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
            Start-Sleep -Seconds 3
            $installed = $true
        } catch {
            Warn "winget install echoue."
        }
    }

    # Fallback : download direct
    if (-not $installed) {
        try {
            Info "Telechargement de l'installeur Ollama ..."
            $installerPath = Join-Path $env:TEMP "OllamaSetup.exe"
            Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installerPath -UseBasicParsing
            Info "Lancement de l'installeur (suivre les instructions) ..."
            Start-Process -FilePath $installerPath -Wait
            Start-Sleep -Seconds 3
            $installed = $true
        } catch {
            Fail "Impossible de telecharger/lancer l'installeur."
            Write-Host "     Installe manuellement : https://ollama.com/download"
        }
    }

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

    $ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaPath) {
        Ok "Ollama installe avec succes."
    } else {
        Warn "Ollama installe mais pas encore dans le PATH."
        Write-Host "     Ferme et re-ouvre PowerShell, puis relance ce script."
    }
}

# --------------------------------------------------------------
# 2. Python 3
# --------------------------------------------------------------
$pythonCmd = $null
foreach ($candidate in @("python3", "python", "py")) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            $pyMajor = & $candidate -c "import sys; print(sys.version_info.major)" 2>$null
            if ($pyMajor -eq "3") {
                $pythonCmd = $candidate
                break
            }
        } catch {}
    }
}

if ($pythonCmd) {
    $pyVer = & $pythonCmd --version 2>&1
    Ok "Python 3 trouve : $pythonCmd ($pyVer)"
} else {
    Info "Python 3 non trouve. Installation en cours ..."

    $installed = $false

    # Tentative winget
    $wingetPath = Get-Command winget -ErrorAction SilentlyContinue
    if ($wingetPath) {
        try {
            Info "Installation via winget ..."
            winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
            Start-Sleep -Seconds 5
            $installed = $true
        } catch {
            Warn "winget install Python echoue."
        }
    }

    # Fallback : Microsoft Store ou download
    if (-not $installed) {
        try {
            Info "Telechargement de Python depuis python.org ..."
            $pyInstaller = Join-Path $env:TEMP "python-installer.exe"
            Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe" -OutFile $pyInstaller -UseBasicParsing
            Info "Lancement installeur Python (InstallAllUsers, PrependPath) ..."
            Start-Process -FilePath $pyInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait
            Start-Sleep -Seconds 5
            $installed = $true
        } catch {
            Fail "Impossible d'installer Python automatiquement."
            Write-Host "     Installe manuellement : https://www.python.org/downloads/"
            exit 1
        }
    }

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Start-Sleep -Seconds 2

    foreach ($candidate in @("python3", "python", "py")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            try {
                $pyMajor = & $candidate -c "import sys; print(sys.version_info.major)" 2>$null
                if ($pyMajor -eq "3") {
                    $pythonCmd = $candidate
                    break
                }
            } catch {}
        }
    }

    if ($pythonCmd) {
        Ok "Python 3 installe : $pythonCmd"
    } else {
        Fail "Python 3 introuvable apres installation."
        Write-Host "     Ferme et re-ouvre PowerShell, puis relance ce script."
        exit 1
    }
}

# --------------------------------------------------------------
# 3. pip
# --------------------------------------------------------------
try {
    & $pythonCmd -m pip --version 2>$null | Out-Null
    Ok "pip disponible."
} catch {
    Info "pip non trouve. Installation ..."
    try {
        & $pythonCmd -m ensurepip --upgrade
        Start-Sleep -Seconds 2
        Ok "pip installe."
    } catch {
        Fail "Impossible d'installer pip."
        exit 1
    }
}

# --------------------------------------------------------------
# 4. venv
# --------------------------------------------------------------
if (Test-Path $VenvDir) {
    Ok "venv existant detecte : $VenvDir"
} else {
    Info "Creation du venv ..."
    & $pythonCmd -m venv $VenvDir
    Start-Sleep -Seconds 3
    Ok "venv cree : $VenvDir"
}

Info "Activation du venv ..."
$activateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
} else {
    # Fallback pour certaines versions
    $activateBat = Join-Path $VenvDir "Scripts\activate.bat"
    if (Test-Path $activateBat) {
        cmd /c "$activateBat"
    } else {
        Warn "Script d'activation introuvable. Activation manuelle requise."
    }
}
Start-Sleep -Seconds 2
Ok "venv actif."

# --------------------------------------------------------------
# 5. Install dependencies
# --------------------------------------------------------------
if (Test-Path $ReqFile) {
    Info "Installation des dependances ..."
    & pip install --upgrade pip -q
    & pip install -r $ReqFile -q
    Start-Sleep -Seconds 2
    Ok "Dependances installees."
} else {
    Warn "requirements.txt non trouve - skip."
}

# --------------------------------------------------------------
# 6. Done
# --------------------------------------------------------------
Write-Host ""
Write-Host "============================================================"
Write-Host "   Installation terminee !" -ForegroundColor Green
Write-Host "============================================================"
Write-Host ""
Write-Host "  Pour lancer Pro-Prompt :" -ForegroundColor White
Write-Host ""
Write-Host "  cd `"$ScriptDir`"" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "  python prompt_expert_enhence.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "  (ou en une ligne) :" -ForegroundColor White
Write-Host ""
Write-Host "  cd `"$ScriptDir`" ; .\.venv\Scripts\Activate.ps1 ; python prompt_expert_enhence.py" -ForegroundColor Cyan
Write-Host ""

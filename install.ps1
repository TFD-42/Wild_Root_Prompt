# ============================================================
#  Prompturgy Installer — Windows (PowerShell)
#  Installs Ollama, Python 3, creates venv, installs deps,
#  creates Prompturgy.bat launcher
# ============================================================

$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir    = Join-Path $ScriptDir ".venv"
$ReqFile    = Join-Path $ScriptDir "requirements.txt"
$MainScript = Join-Path $ScriptDir "prompt_expert_enhance.py"
$Launcher   = Join-Path $ScriptDir "Prompturgy.bat"

function Info($msg)  { Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Ok($msg)    { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Warn($msg)  { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Fail($msg)  { Write-Host "[FAIL]  $msg" -ForegroundColor Red; exit 1 }
function Step($msg)  { Write-Host "`n$msg" -ForegroundColor White }

Write-Host ""
Write-Host "============================================================"
Write-Host "   Prompturgy  -  Windows Installer"
Write-Host "============================================================"
Write-Host ""

# --------------------------------------------------------------
# 1. Ollama
# --------------------------------------------------------------
Step "1/6  Checking Ollama"
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Ok "Ollama already installed."
    # Start service if not running
    try {
        Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2 | Out-Null
    } catch {
        Info "Starting Ollama service..."
        Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
    }
} else {
    Info "Installing Ollama..."
    $OllamaInstaller = Join-Path $env:TEMP "OllamaSetup.exe"
    try {
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $OllamaInstaller -UseBasicParsing
        Start-Process $OllamaInstaller -Wait
        Start-Sleep -Seconds 3
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        if (Get-Command ollama -ErrorAction SilentlyContinue) {
            Ok "Ollama installed."
            Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 3
        } else {
            Warn "Ollama installed but not found in PATH yet. Restart terminal if needed."
        }
    } catch {
        Warn "Could not auto-install Ollama. Download manually: https://ollama.com/download"
    }
}

# --------------------------------------------------------------
# 2. Python 3
# --------------------------------------------------------------
Step "2/6  Checking Python 3"
$PythonCmd = $null
foreach ($candidate in @("python", "python3")) {
    try {
        $ver = & $candidate --version 2>&1
        $major = & $candidate -c "import sys; print(sys.version_info.major)" 2>$null
        $minor = & $candidate -c "import sys; print(sys.version_info.minor)" 2>$null
        if ($major -eq "3" -and [int]$minor -ge 8) {
            $PythonCmd = $candidate
            Ok "Python found: $candidate ($ver)"
            break
        }
    } catch {}
}

if (-not $PythonCmd) {
    Info "Python 3.8+ not found. Installing via winget..."
    try {
        winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements
        Start-Sleep -Seconds 5
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        foreach ($candidate in @("python", "python3")) {
            try {
                $major = & $candidate -c "import sys; print(sys.version_info.major)" 2>$null
                if ($major -eq "3") { $PythonCmd = $candidate; break }
            } catch {}
        }
        if ($PythonCmd) { Ok "Python installed: $PythonCmd" }
        else { Fail "Python not found after install. Please install Python 3.11+ manually from python.org." }
    } catch {
        Fail "winget not available. Install Python 3.11+ from https://python.org/downloads"
    }
}

# --------------------------------------------------------------
# 3. venv
# --------------------------------------------------------------
Step "3/6  Creating virtual environment"

if (Test-Path $VenvDir) {
    Ok "Existing venv: $VenvDir"
} else {
    Info "Creating venv..."
    & $PythonCmd -m venv $VenvDir
    if (-not $?) { Fail "venv creation failed." }
    # Wait for venv to fully initialize — Windows venv can be slow
    Start-Sleep -Seconds 4
    Ok "venv created."
}

$PythonVenv = Join-Path $VenvDir "Scripts\python.exe"
$PipVenv    = Join-Path $VenvDir "Scripts\pip.exe"

if (-not (Test-Path $PythonVenv)) {
    # Sometimes takes a bit longer on slow machines
    Start-Sleep -Seconds 3
    if (-not (Test-Path $PythonVenv)) {
        Fail "venv python.exe not found at $PythonVenv"
    }
}
Ok "venv ready: $PythonVenv"

# --------------------------------------------------------------
# 4. pip + dependencies
# --------------------------------------------------------------
Step "4/6  Installing dependencies"

Info "Upgrading pip..."
& $PipVenv install --upgrade pip -q
Start-Sleep -Seconds 2
Ok "pip upgraded."

if (Test-Path $ReqFile) {
    Info "Installing from requirements.txt..."
    & $PipVenv install -r $ReqFile -q
    Start-Sleep -Seconds 2
    Ok "Dependencies installed (requests, flask)."
} else {
    Info "requirements.txt not found — installing manually."
    & $PipVenv install requests flask -q
    Start-Sleep -Seconds 2
    Ok "requests + flask installed."
}

# --------------------------------------------------------------
# 5. Create Prompturgy.bat launcher
# --------------------------------------------------------------
Step "5/6  Creating launcher"

$LauncherContent = @"
@echo off
cd /d "$ScriptDir"
call ".venv\Scripts\activate.bat"

:: Start Ollama if not running
curl -s "http://localhost:11434/api/tags" >nul 2>&1
if errorlevel 1 (
    echo Starting Ollama...
    start "" /B ollama serve
    timeout /t 3 /nobreak >nul
)

python prompt_expert_enhance.py --web %*
"@

$LauncherContent | Out-File -FilePath $Launcher -Encoding utf8 -Force
Ok "Launcher created: $Launcher"

# --------------------------------------------------------------
# 6. Done
# --------------------------------------------------------------
Step "6/6  Installation complete"
Write-Host ""
Write-Host "============================================================"
Write-Host "   Installation complete!" -ForegroundColor Green
Write-Host "============================================================"
Write-Host ""
Write-Host "  Launch options:"
Write-Host ""
Write-Host "  Double-click:  Prompturgy.bat          <- opens web UI" -ForegroundColor Cyan
Write-Host "  PowerShell:    .\.venv\Scripts\Activate.ps1 ; python prompt_expert_enhance.py" -ForegroundColor Cyan
Write-Host "  CLI:           .\.venv\Scripts\Activate.ps1 ; python prompt_expert_enhance.py generate `"your task`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Web UI URL:  http://localhost:7860" -ForegroundColor Yellow
Write-Host ""

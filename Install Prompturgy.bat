@echo off
REM Double-click entry point for Windows — runs the full installer via PowerShell.
REM (Equivalent one-line terminal command: powershell -ExecutionPolicy Bypass -File install.ps1)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1
pause

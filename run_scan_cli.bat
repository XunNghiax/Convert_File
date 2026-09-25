@echo off
chcp 65001 > nul
cd /d "%~dp0"
set PYTHONPATH=%~dp0
set PYTHONIOENCODING=utf-8

if exist ".\venv\Scripts\python.exe" (
    ".\venv\Scripts\python.exe" scripts\scan_cli.py
) else (
    python scripts\scan_cli.py
)

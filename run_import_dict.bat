@echo off
chcp 65001 > nul
title Novel Translation Refiner - Import Scanned Dictionary
cd /d "%~dp0"

echo ========================================================================
echo       NOVEL TRANSLATION REFINER - KHOI CHAY DONG BO TU DIEN
echo ========================================================================
echo.

if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe scripts\import_scanned_dict.py %*
) else (
    python scripts\import_scanned_dict.py %*
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Co loi xay ra trong qua trinh thuc thi.
    pause
)

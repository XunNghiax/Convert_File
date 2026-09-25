@echo off
chcp 65001 > nul
title Novel Translation Refiner - Import Scanned Dictionary
cd /d "%~dp0"

echo ========================================================================
echo       NOVEL TRANSLATION REFINER - KHOI CHAY DONG BO TU DIEN
echo ========================================================================
echo.

set "PYTHON_EXE=python"
if exist venv\Scripts\python.exe set "PYTHON_EXE=venv\Scripts\python.exe"

if "%~1"=="" (
    rem Mac dinh khong truyen tham so: Khoi chay Wizard voi lua chon 1 la import.txt
    %PYTHON_EXE% scripts\import_scanned_dict.py
) else if exist "%~1" (
    rem Keo tha file hoac truyen truc tiep duong dan file vao batch
    %PYTHON_EXE% scripts\import_scanned_dict.py --file "%~1"
) else (
    rem Truyen cac tham so dong lenh CLI (vi du: --dry-run, --tag ...)
    %PYTHON_EXE% scripts\import_scanned_dict.py %*
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Co loi xay ra trong qua trinh thuc thi.
    pause
)

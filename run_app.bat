@echo off
chcp 65001 > nul
cd /d "%~dp0"
set PYTHONPATH=%~dp0
set PYTHONIOENCODING=utf-8

echo ===================================================
echo runing http://localhost:8501
echo ===================================================

if exist ".\venv\Scripts\streamlit.exe" (
    ".\venv\Scripts\streamlit.exe" run src\ui\app.py
) else (
    echo Khong tim thay moi truong venv! Dang thu chay bang streamlit he thong...
    streamlit run src\ui\app.py
)

pause

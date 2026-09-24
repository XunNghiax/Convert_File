@echo off
chcp 65001 > nul
echo ===================================================
echo   KHOI DONG TRINH CONVERT TRUYEN DICH THO
echo ===================================================
.\venv\Scripts\streamlit.exe run src/ui/app.py
pause

@echo off
setlocal
cd /d "%~dp0"
start "ACI-Text-Tools" ".venv\Scripts\pythonw.exe" "main.py"

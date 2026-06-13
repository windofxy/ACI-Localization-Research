@echo off
setlocal
cd /d "%~dp0"
start "ACI-Font-Tools" ".venv\Scripts\pythonw.exe" "main.py"

@echo off
setlocal
cd /d "%~dp0"
if exist "ReSkate Deck Tool.exe" (
  start "" "ReSkate Deck Tool.exe"
  exit /b
)
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "Lenticular Deck Creator.pyw"
  exit /b
)
py -3.12 "Lenticular Deck Creator.pyw"

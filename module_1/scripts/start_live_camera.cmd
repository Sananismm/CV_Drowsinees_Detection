@echo off
setlocal
cd /d "%~dp0.."
set "SG1_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%SG1_PYTHON%" (
  echo SG-1 Python environment not found. See docs\VSCODE_LIVE_DEMO.md for setup.
  pause
  exit /b 1
)
"%SG1_PYTHON%" "%CD%\scripts\live_demo.py" --camera 0
if errorlevel 1 (
  echo Webcam demo failed. See docs\VSCODE_LIVE_DEMO.md for troubleshooting.
  pause
  exit /b 1
)
endlocal

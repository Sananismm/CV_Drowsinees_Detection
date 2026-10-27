@echo off
setlocal
cd /d "%~dp0.."
set "SG1_PYTHON=%CD%\.venv\Scripts\python.exe"
set "SG1_VIDEO=%USERPROFILE%\Downloads\P10427801_na.mp4"
if not exist "%SG1_PYTHON%" (
  echo SG-1 Python environment not found. See docs\VSCODE_LIVE_DEMO.md for setup.
  pause
  exit /b 1
)
if not exist "%SG1_VIDEO%" (
  echo Downloaded video not found: %SG1_VIDEO%
  echo See docs\VSCODE_LIVE_DEMO.md for another video.
  pause
  exit /b 1
)
"%SG1_PYTHON%" "%CD%\scripts\live_demo.py" --video "%SG1_VIDEO%"
if errorlevel 1 (
  echo Saved-video demo failed. See docs\VSCODE_LIVE_DEMO.md for troubleshooting.
  pause
  exit /b 1
)
endlocal

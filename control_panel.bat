@echo off
setlocal
cd /d "%~dp0"
echo Starting Bitmap Lyrics Studio...
echo Project folder: %CD%
echo.
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher 'py' was not found.
  echo Install Python from python.org and enable the Python Launcher, then try again.
  pause
  exit /b 1
)
py -3.12 control_panel.py
if errorlevel 1 (
  echo.
  echo The control panel exited with an error. Read the message above.
  pause
)
endlocal

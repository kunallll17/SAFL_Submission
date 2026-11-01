@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat first to install the local dependencies.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m vaaniverify %*
if errorlevel 1 pause

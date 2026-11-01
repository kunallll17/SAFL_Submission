@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m vaaniverify.evaluate
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m vaaniverify.mutations
if errorlevel 1 exit /b 1

@echo off
setlocal
cd /d "%~dp0"
echo EXPERIMENTAL: Native ship reward bridge. No gameplay validation yet.
echo Open the game using your existing CapsLockFix launcher first.
echo This attaches an optional pyMHF hook; it does not replace your launcher.
if not exist "runtime\native-bridge-venv\Scripts\python.exe" (
    python -m venv runtime\native-bridge-venv
    if errorlevel 1 exit /b 1
)
runtime\native-bridge-venv\Scripts\python.exe -c "import importlib.metadata as m; raise SystemExit(m.version('pymhf') != '0.2.5')" >nul 2>nul
if errorlevel 1 (
    runtime\native-bridge-venv\Scripts\python.exe -m pip install "pymhf[gui]==0.2.5"
    if errorlevel 1 exit /b 1
)
runtime\native-bridge-venv\Scripts\python.exe -m pymhf run native_bridge\ship_rewards.py
if errorlevel 1 pause

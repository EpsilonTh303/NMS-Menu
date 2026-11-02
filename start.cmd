@echo off
cd /d "%~dp0"
python -u tools\launch_menu.py %*
set "menu_exit=%errorlevel%"
if not "%menu_exit%"=="0" pause
exit /b %menu_exit%

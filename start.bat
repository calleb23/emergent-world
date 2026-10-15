@echo off
rem Emergent World: get the latest code from GitHub, then watch it live in your browser.
rem Double-click this file. It keeps checking GitHub and restarts on new code by itself.
cd /d "%~dp0"
python -m pip install --quiet --disable-pip-version-check numpy
set FIRST=1
:loop
git pull --ff-only --quiet
if "%FIRST%"=="1" (
  python -m emergent_world.live --auto-update 2
) else (
  python -m emergent_world.live --auto-update 2 --no-browser
)
if %ERRORLEVEL%==3 (
  set FIRST=0
  goto loop
)
pause

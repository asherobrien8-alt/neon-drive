@echo off
rem Neon Drive cover art: builds .rechord\ARTPACK.BIN on the player so
rem Now Playing can show album covers (turn it on with MENU > Cover art).
rem Needs Python 3 (python.org, tick "Add python.exe to PATH").
setlocal
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% -c "import PIL, mutagen" 2>nul || %PY% -m pip install --quiet pillow mutagen
echo.
set /p DRV=Player drive letter (the Echo Mini, e.g. E): 
set /p SDD=SD card drive letter (leave empty if none): 
if "%SDD%"=="" (
  %PY% "%~dp0artpack.py" --root %DRV%:\ --large 80 --small 48
) else (
  %PY% "%~dp0artpack.py" --root %DRV%:\ --extra-root %SDD%:\ --large 80 --small 48
)
echo.
echo Done. Eject the player, then on it: MENU ^> Cover art ^> on.
pause

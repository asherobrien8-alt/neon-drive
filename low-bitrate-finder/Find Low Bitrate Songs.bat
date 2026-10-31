@echo off
rem Double-click, or drag your music folder onto this file.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Find-LowBitrate.ps1" %*
echo.
pause

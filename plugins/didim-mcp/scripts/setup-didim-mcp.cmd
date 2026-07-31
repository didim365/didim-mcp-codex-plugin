@echo off
setlocal
rem Double-click launcher for setup-didim-mcp.ps1.
rem ExecutionPolicy Bypass applies to this process only; no admin rights needed.
rem "%~dp0" is this script's folder (with trailing backslash); quotes handle spaces.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-didim-mcp.ps1"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo Setup finished. You can close this window.
) else (
  echo Setup did not complete. Exit code: %RC%. See the messages above.
)
echo.
pause
endlocal

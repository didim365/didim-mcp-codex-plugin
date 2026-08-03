@echo off
chcp 65001 >nul
setlocal
rem Double-click launcher for setup-didim-mcp.ps1.
rem chcp 65001 = UTF-8 code page so Korean output is not mangled.
rem ExecutionPolicy Bypass applies to this process only; no admin rights needed.
rem "%~dp0" is this script's folder (with trailing backslash); quotes handle spaces.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-didim-mcp.ps1"
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

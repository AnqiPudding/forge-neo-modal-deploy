@echo off
setlocal

cd /d "%~dp0"

if not defined MODAL_APP_NAME set "MODAL_APP_NAME=forge-neo"
set "PYTHONIOENCODING=utf-8"

echo Stopping Modal app %MODAL_APP_NAME% ...
modal app stop "%MODAL_APP_NAME%" --yes
exit /b %ERRORLEVEL%


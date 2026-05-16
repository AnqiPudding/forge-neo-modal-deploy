@echo off
setlocal

cd /d "%~dp0"
modal run modal_app.py --show-logs
exit /b %ERRORLEVEL%


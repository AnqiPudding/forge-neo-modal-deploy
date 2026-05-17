@echo off
setlocal

cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "MODAL_FORCE_IMAGE_PULL=0"
modal run modal_app.py --show-logs
exit /b %ERRORLEVEL%

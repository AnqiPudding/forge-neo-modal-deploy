@echo off
setlocal

cd /d "%~dp0"

where modal >nul 2>nul
if errorlevel 1 (
    echo Modal CLI was not found. Run login_modal.bat first.
    exit /b 1
)

set "MODAL_GPU=L40S"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if not defined MODAL_APP_NAME set "MODAL_APP_NAME=forge-neo"
if not defined FORGE_NEO_IMAGE set "FORGE_NEO_IMAGE=ghcr.io/anqipudding/forge-neo-modal-deploy:latest"

echo Deploying %MODAL_APP_NAME% on Modal with GPU=%MODAL_GPU% ...
modal deploy modal_app.py
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Deploy failed with exit code %EXIT_CODE%.
    exit /b %EXIT_CODE%
)

echo.
echo Deploy complete. Opening Forge WebUI and JupyterLab...
call "%~dp0open_webui_and_jupyter.bat"
exit /b %ERRORLEVEL%

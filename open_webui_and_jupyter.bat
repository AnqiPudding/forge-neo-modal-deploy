@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

where modal >nul 2>nul
if errorlevel 1 (
    echo Modal CLI was not found. Run login_modal.bat first.
    exit /b 1
)

if not defined JUPYTER_TOKEN set "JUPYTER_TOKEN=forge-neo"
set "PYTHONIOENCODING=utf-8"

if defined MODAL_WORKSPACE (
    set "WORKSPACE=%MODAL_WORKSPACE%"
) else (
    for /f "usebackq delims=" %%A in (`modal profile current 2^>nul`) do (
        if not defined WORKSPACE set "WORKSPACE=%%A"
    )
)

if not defined WORKSPACE (
    echo Could not detect your Modal workspace/profile.
    echo Set MODAL_WORKSPACE and run this again, for example:
    echo set MODAL_WORKSPACE=your-workspace
    exit /b 1
)

set "FORGE_URL=https://!WORKSPACE!--forge.modal.run"
set "JUPYTER_URL=https://!WORKSPACE!--jupyter.modal.run/lab?token=!JUPYTER_TOKEN!"

echo Opening Forge WebUI:
echo !FORGE_URL!
start "" "!FORGE_URL!"

echo.
echo Opening JupyterLab:
echo !JUPYTER_URL!
start "" "!JUPYTER_URL!"

exit /b 0


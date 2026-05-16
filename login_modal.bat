@echo off
setlocal

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH.
    exit /b 1
)

echo Installing Modal client for the current user...
python -m pip install --user -r requirements.txt
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
if "%~1"=="" (
    echo Opening Modal browser login for the default profile...
    modal setup
) else (
    echo Opening Modal browser login for profile "%~1"...
    modal setup --profile "%~1"
)

exit /b %ERRORLEVEL%


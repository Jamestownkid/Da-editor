@echo off
REM Da Editor - Windows Run Script
REM ================================
REM one-click launcher for the app
REM
REM usage: double-click run.bat

echo =========================================
echo   DA EDITOR - B-Roll Automation
echo =========================================
echo.

REM change to script directory
cd /d "%~dp0"

REM check if electron exists
if exist "electron\package.json" (
    REM check if node_modules exists
    if not exist "electron\node_modules" (
        echo First run detected - setting up...
        python setup.py
    )
    
    echo Starting Electron app...
    cd electron
    npm run dev
) else (
    echo Starting Python app...
    python main.py
)

pause

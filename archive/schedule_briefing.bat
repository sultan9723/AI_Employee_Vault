@echo off
REM Schedule CEO Briefing - Run this file as Administrator
REM Right-click → Run as Administrator

setlocal enabledelayedexpansion

REM Get the vault directory (parent of this batch file)
set VAULT_DIR=%~dp0
set VAULT_DIR=%VAULT_DIR:~0,-1%
set PYTHON_SCRIPT=%VAULT_DIR%\ceo_briefing.py
set PYTHON_EXE=python.exe

echo.
echo ======================================================================
echo  AI EMPLOYEE - CEO BRIEFING SCHEDULER (Windows Task Scheduler)
echo ======================================================================
echo.
echo Vault Directory: %VAULT_DIR%
echo Python Script:  %PYTHON_SCRIPT%
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This batch file must be run as Administrator!
    echo.
    echo Solution: Right-click this file and select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

echo [+] Running as Administrator - proceeding...
echo.

REM Create the task using schtasks
echo [*] Creating scheduled task "AIEmployee-CEOBriefing"...
schtasks /create /tn "AIEmployee-CEOBriefing" /tr "%PYTHON_EXE% \"%PYTHON_SCRIPT%\"" /sc weekly /d MON /st 08:00 /f

if %errorLevel% equ 0 (
    echo.
    echo ======================================================================
    echo [+] SUCCESS! CEO Briefing scheduled
    echo ======================================================================
    echo.
    echo Task Name:     AIEmployee-CEOBriefing
    echo Schedule:      Every Monday at 08:00 AM
    echo Action:        Run %PYTHON_SCRIPT%
    echo.
    echo Commands:
    echo   - Run manually:    schtasks /run /tn "AIEmployee-CEOBriefing"
    echo   - View task:       schtasks /query /tn "AIEmployee-CEOBriefing" /v
    echo   - Remove task:     schtasks /delete /tn "AIEmployee-CEOBriefing" /f
    echo.
) else (
    echo.
    echo ======================================================================
    echo [-] FAILED to create scheduled task
    echo ======================================================================
    echo.
    echo Error code: %errorLevel%
    echo.
    echo Troubleshooting:
    echo   1. Make sure you ran this file as Administrator
    echo   2. Check that %PYTHON_SCRIPT% exists
    echo   3. Verify python.exe is in your PATH
    echo.
    pause
    exit /b 1
)

echo [+] Verifying task was created...
schtasks /query /tn "AIEmployee-CEOBriefing" /fo list

pause

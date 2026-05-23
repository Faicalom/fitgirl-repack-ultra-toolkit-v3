@echo off
chcp 65001 >nul 2>&1
title FitGirl Repack Ultra Toolkit v3

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://www.python.org/
    pause
    exit /b 1
)

if not exist _toolkit_ui.py (
    echo [ERROR] _toolkit_ui.py not found.
    pause & exit /b 1
)
if not exist Page_Link_Extractor_speed.py (
    echo [ERROR] Page_Link_Extractor_speed.py not found.
    pause & exit /b 1
)
if not exist Download_Manager_Sender_Speed.py (
    echo [ERROR] Download_Manager_Sender_Speed.py not found.
    pause & exit /b 1
)
if not exist Direct_Link_Resolver.py (
    echo [ERROR] Direct_Link_Resolver.py not found.
    pause & exit /b 1
)
if not exist Direct_Link_Resolver_Slow.py (
    echo [ERROR] Direct_Link_Resolver_Slow.py not found.
    pause & exit /b 1
)
if not exist toolkit_guard.py (
    echo [ERROR] toolkit_guard.py not found.
    pause & exit /b 1
)

python toolkit_guard.py runtime-check
if errorlevel 1 (
    echo [ERROR] Runtime check failed. Fix the errors above first.
    pause & exit /b 1
)

cls
python _toolkit_ui.py init
python _toolkit_ui.py banner

echo Stage 1 - Paste the FitGirl game page URL below
echo.

python Page_Link_Extractor_speed.py
if errorlevel 1 (
    python _toolkit_ui.py log_error "Stage 1 failed"
    echo [ERROR] Stage 1 failed. See failed_links.txt
    pause & exit /b 1
)

if not exist fuckingfast_links.txt (
    python _toolkit_ui.py log_error "fuckingfast_links.txt not created"
    echo [ERROR] No links found.
    pause & exit /b 1
)

echo.
python _toolkit_ui.py progress

echo Stage 2 - File selection and download
echo.

python Download_Manager_Sender_Speed.py
if errorlevel 1 (
    python _toolkit_ui.py log_error "Stage 2 failed"
    echo [ERROR] Stage 2 error. See failed_links.txt
)

python _toolkit_ui.py end

echo.
echo Done. Log saved in failed_links.txt
echo.
pause

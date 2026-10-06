@echo off
title LANBOX Client
echo Starting LANBOX Client...
python client/main_client.py
if errorlevel 1 (
    echo.
    echo [!] If python is not found or packages are missing, run:
    echo     pip install -r requirements.txt
    pause
)

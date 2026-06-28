@echo off
cd /d "%~dp0"
start "" powershell -ExecutionPolicy Bypass -File ".\scripts\start_dashboard.ps1"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8787"

@echo off
cd /d "%~dp0"
powershell.exe -NoExit -ExecutionPolicy Bypass -File ".\scripts\reset-dev-data.ps1"


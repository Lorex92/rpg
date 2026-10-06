@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=
python --version >nul 2>&1 && set PY=python
if "%PY%"=="" ( py -3 --version >nul 2>&1 && set PY=py -3 )
if "%PY%"=="" (
    echo Python non trovato. Fai prima doppio clic su installa.bat
    pause
    exit /b 1
)
%PY% FacciaTasti.py
if errorlevel 1 pause

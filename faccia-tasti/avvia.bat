@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYW=
python --version >nul 2>&1 && set PYW=pythonw
if "%PYW%"=="" ( py -3 --version >nul 2>&1 && set PYW=pyw -3 )
if "%PYW%"=="" (
    echo Python non trovato. Fai prima doppio clic su installa.bat
    pause
    exit /b 1
)
rem Avvia senza finestra nera: gli eventuali errori finiscono in errori.txt
start "" %PYW% FacciaTasti.py

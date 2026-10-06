@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo   FACCIA -^> TASTI  -  installazione
echo ==========================================
echo.

set PY=
python --version >nul 2>&1 && set PY=python
if "%PY%"=="" ( py -3 --version >nul 2>&1 && set PY=py -3 )
if "%PY%"=="" (
    echo Python non e' installato ^(o non e' nel PATH^).
    echo.
    echo Scaricalo da  https://www.python.org/downloads/   ^(versione 3.12^)
    echo e durante l'installazione METTI LA SPUNTA su "Add python.exe to PATH".
    echo Poi fai di nuovo doppio clic su installa.bat
    echo.
    pause
    exit /b 1
)

echo Trovato Python:
%PY% --version
echo.
echo Installo le librerie necessarie (ci vuole qualche minuto)...
echo.
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Qualcosa e' andato storto durante l'installazione delle librerie.
    echo Controlla la connessione a internet e riprova.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   Installazione completata!
echo   Ora fai doppio clic su  avvia.bat
echo ==========================================
pause

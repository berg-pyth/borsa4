@echo off
echo Creazione ambiente virtuale per BorsaNew_app...

REM Controlla se Python è installato
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRORE: Python non trovato. Installa Python prima di continuare.
    pause
    exit /b 1
)

REM Crea l'ambiente virtuale
echo Creazione ambiente virtuale...
python -m venv venv

REM Attiva l'ambiente virtuale
echo Attivazione ambiente virtuale...
call venv\Scripts\activate.bat

REM Aggiorna pip
echo Aggiornamento pip...
python -m pip install --upgrade pip

REM Installa le dipendenze
echo Installazione dipendenze...
pip install -r requirements.txt

echo.
echo ========================================
echo Ambiente virtuale creato con successo!
echo ========================================
echo.
echo Per attivare l'ambiente virtuale in futuro, usa:
echo   venv\Scripts\activate.bat
echo.
echo Per avviare l'app Streamlit:
echo   streamlit run Homepage.py
echo.
pause
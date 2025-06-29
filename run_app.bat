@echo off
echo Avvio BorsaNew_app...

REM Controlla se l'ambiente virtuale esiste
if not exist "venv\Scripts\activate.bat" (
    echo ERRORE: Ambiente virtuale non trovato.
    echo Esegui prima setup_venv.bat per creare l'ambiente virtuale.
    pause
    exit /b 1
)

REM Attiva l'ambiente virtuale
call venv\Scripts\activate.bat

REM Avvia l'applicazione Streamlit
streamlit run Homepage.py

pause
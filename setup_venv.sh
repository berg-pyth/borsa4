#!/bin/bash

echo "Creazione ambiente virtuale per BorsaNew_app..."

# Controlla se Python è installato
if ! command -v python3 &> /dev/null; then
    echo "ERRORE: Python3 non trovato. Installa Python prima di continuare."
    exit 1
fi

# Crea l'ambiente virtuale
echo "Creazione ambiente virtuale..."
python3 -m venv venv

# Attiva l'ambiente virtuale
echo "Attivazione ambiente virtuale..."
source venv/bin/activate

# Aggiorna pip
echo "Aggiornamento pip..."
python -m pip install --upgrade pip

# Installa le dipendenze
echo "Installazione dipendenze..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Ambiente virtuale creato con successo!"
echo "========================================"
echo ""
echo "Per attivare l'ambiente virtuale in futuro, usa:"
echo "  source venv/bin/activate"
echo ""
echo "Per avviare l'app Streamlit:"
echo "  streamlit run Homepage.py"
echo ""
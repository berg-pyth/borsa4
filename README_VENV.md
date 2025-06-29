# Guida Ambiente Virtuale - BorsaNew_app

## Configurazione Iniziale

### Windows
1. Esegui `setup_venv.bat` facendo doppio clic
2. Attendi il completamento dell'installazione

### Linux/macOS
1. Rendi eseguibile lo script: `chmod +x setup_venv.sh`
2. Esegui: `./setup_venv.sh`

## Utilizzo Quotidiano

### Windows
- **Avvio rapido**: Esegui `run_app.bat`
- **Attivazione manuale**: `venv\Scripts\activate.bat`

### Linux/macOS
- **Attivazione**: `source venv/bin/activate`
- **Avvio app**: `streamlit run Homepage.py`

## Gestione Dipendenze

### Aggiungere nuove librerie
```bash
# Attiva l'ambiente virtuale
pip install nome_libreria
pip freeze > requirements.txt  # Aggiorna requirements.txt
```

### Aggiornare dipendenze esistenti
```bash
pip install --upgrade nome_libreria
pip freeze > requirements.txt
```

## Vantaggi dell'Ambiente Virtuale

✅ **Isolamento**: Le dipendenze sono separate dal sistema  
✅ **Riproducibilità**: Stesso ambiente su macchine diverse  
✅ **Sicurezza**: Nessun conflitto con altre versioni Python  
✅ **Portabilità**: Facile condivisione del progetto  

## Risoluzione Problemi

### Errore "Python non trovato"
- Installa Python da python.org
- Assicurati che sia nel PATH di sistema

### Errore permessi
- Su Windows: Esegui come amministratore
- Su Linux/macOS: Usa `sudo` se necessario

### Reinstallazione completa
1. Elimina la cartella `venv`
2. Riesegui lo script di setup
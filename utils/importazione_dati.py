# Borsa2_app/utils/importazione_dati.py

import pandas as pd
import yfinance as yf
import datetime
import streamlit as st # Useremo st.cache_data per ottimizzare

def load_tickers_from_csv(file_path="tickers.csv"):
    """
    Carica i simboli dei ticker e i nomi delle aziende da un file CSV.
    Il CSV dovrebbe avere le colonne 'Symbol' e 'Company'.
    Ritorna un DataFrame con i ticker e i nomi, o None in caso di errore.
    """
    try:
        # Assumiamo che il file tickers.csv sia nella root del progetto (Borsa2_app)
        df_tickers = pd.read_csv(file_path)
        if 'Symbol' not in df_tickers.columns:
            st.error(f"Il file '{file_path}' deve contenere una colonna 'Symbol'.")
            return None
        return df_tickers
    except FileNotFoundError:
        st.error(f"Errore: Il file '{file_path}' non è stato trovato nella directory principale del progetto.")
        return None
    except Exception as e:
        st.error(f"Errore durante la lettura del file '{file_path}': {e}")
        return None

@st.cache_data(ttl=3600) # Memorizza in cache i dati per 1 ora (3600 secondi)
def download_stock_data(ticker_symbol: str, start_date: datetime.date, end_date: datetime.date):
    """
    Scarica i dati storici di un singolo titolo azionario utilizzando yfinance.
    I dati vengono memorizzati in cache per velocizzare le richieste ripetute.

    Args:
        ticker_symbol (str): Il simbolo del titolo azionario (es. 'AAPL').
        start_date (datetime.date): La data di inizio per i dati.
        end_date (datetime.date): La data di fine per i dati.

    Returns:
        pd.DataFrame: Un DataFrame di Pandas con i dati OHLCV, o None in caso di errore.
    """
    if not isinstance(ticker_symbol, str) or not ticker_symbol:
        st.warning("Simbolo del titolo non valido fornito per il download.")
        return None
    if not isinstance(start_date, datetime.date) or not isinstance(end_date, datetime.date):
        st.warning("Date non valide fornite per il download.")
        return None
    if start_date >= end_date:
        st.warning("La data di inizio deve essere precedente alla data di fine.")
        return None

    try:
        data = yf.download(ticker_symbol, start=start_date, end=end_date)
        if data.empty:
            st.warning(f"Nessun dato trovato per il simbolo: {ticker_symbol} nel periodo specificato ({start_date} a {end_date}).")
            return None
        return data
    except Exception as e:
        st.error(f"Errore durante il download dei dati per {ticker_symbol} da Yahoo Finance: {e}")
        return None

# Funzione per ottenere la lista dei simboli e nomi per la selezione in Streamlit
def get_ticker_list_for_selection(file_path="tickers.csv"):
    """
    Prepara una lista di stringhe formattate "Symbol - Company Name" per la selezione utente.
    """
    df_tickers = load_tickers_from_csv(file_path)
    if df_tickers is not None and not df_tickers.empty:
        # Combina Symbol e Company per una visualizzazione più chiara nel selectbox
        df_tickers['Display'] = df_tickers['Symbol'] + ' - ' + df_tickers['Company']
        return df_tickers['Display'].tolist()
    return []

def extract_symbol_from_selection(selected_string: str):
    """
    Estrae il simbolo del ticker da una stringa formattata "Symbol - Company Name".
    """
    if selected_string and ' - ' in selected_string:
        return selected_string.split(' - ')[0].strip()
    return selected_string.strip() # Ritorna la stringa così com'è se il formato non corrisponde
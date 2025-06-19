# data_utils

import streamlit as st
import pandas as pd
import os

# Supponiamo che tickers.csv sia nella cartella principale del progetto (Borsa1_app)
TICKERS_FILEPATH = "tickers.csv"

@st.cache_data
def load_tickers_data(filepath=TICKERS_FILEPATH):
    """
    Carica la lista dei ticker e i loro nomi da un file CSV.
    Ritorna lista ordinata di ticker e dizionario {ticker: nome}.
    Non mostra errori direttamente, ma ritorna liste/dizionari vuoti.
    """
    if not os.path.exists(filepath):
        # Preferiamo gestire l'errore nella pagina che chiama la funzione
        return [], {}

    try:
        df_tickers = pd.read_csv(filepath)
        if 'Ticker' not in df_tickers.columns or 'NomeEsteso' not in df_tickers.columns:
            # Preferiamo gestire l'errore nella pagina chiamante
            return [], {}

        lista_ticker = df_tickers['Ticker'].tolist()
        dizionario_ticker_nomi = dict(zip(df_tickers['Ticker'], df_tickers['NomeEsteso']))

        lista_ticker.sort()

        return lista_ticker, dizionario_ticker_nomi

    except Exception as e:
        # Preferiamo gestire l'errore nella pagina chiamante
        # print(f"Errore interno in load_tickers_data: {e}") # Per debug
        return [], {}

# Puoi aggiungere qui altre funzioni di utilità relative ai dati che potrebbero essere condivise
# in futuro.
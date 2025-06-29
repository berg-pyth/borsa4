# BorsaNew_app/utils/logica_strategie/supertrend_strategy.py

from ..numpy_compat import *
import pandas as pd
import numpy as np
import pandas_ta as ta

class SupertrendStrategy:
    """
    Implementa la strategia di trading basata sull'indicatore Supertrend.
    
    Regole:
    - BUY LONG quando inizia un UPPERTREND (trend=1)
    - SELL LONG quando inizia un LOWERTREND (trend=-1)
    - SHORT quando inizia un LOWERTREND (trend=-1)
    - COVER SHORT quando inizia un UPPERTREND (trend=1)
    """
    
    @staticmethod
    def get_strategy_parameters():
        """
        Restituisce i parametri configurabili della strategia.
        
        Returns:
            dict: Dizionario con i parametri della strategia e le loro configurazioni.
        """
        return {
            "period": {
                "type": "int", 
                "default": 10, 
                "min_value": 5, 
                "max_value": 30, 
                "step": 1, 
                "label": "Periodo ATR"
            },
            "multiplier": {
                "type": "float", 
                "default": 3.0, 
                "min_value": 1.0, 
                "max_value": 6.0, 
                "step": 0.1, 
                "label": "Moltiplicatore"
            }
        }
    
    def __init__(self, df: pd.DataFrame, period: int, multiplier: float):
        """
        Inizializza la strategia con i dati e i parametri.

        Args:
            df (pd.DataFrame): DataFrame di input con dati OHLCV.
            period (int): Periodo per il calcolo dell'ATR.
            multiplier (float): Moltiplicatore per l'ATR.
        """
        self.df = df.copy()  # Lavora su una copia del DataFrame originale
        self.period = period
        self.multiplier = multiplier
        self.processed_df = None

    def generate_signals(self) -> pd.DataFrame:
        """
        Calcola l'indicatore Supertrend e genera i segnali di trading.

        Returns:
            pd.DataFrame: DataFrame originale con l'aggiunta delle colonne dell'indicatore
                          e della colonna 'Signal' (1 per Buy, -1 per Sell, 0 per Hold).
        """
        df_working = self.df.copy()

        # --- Pulizia e Normalizzazione Dati ---
        df_working.columns = [col.upper() for col in df_working.columns]

        required_cols = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
        if not all(col in df_working.columns for col in required_cols):
            print(f"Errore: DataFrame mancante di colonne OHLCV essenziali per Supertrend. Richieste: {required_cols}")
            return pd.DataFrame()

        # --- Calcolo dell'indicatore Supertrend ---
        try:
            # Calcola il Supertrend usando pandas-ta
            supertrend = ta.supertrend(
                high=df_working['HIGH'], 
                low=df_working['LOW'], 
                close=df_working['CLOSE'], 
                length=self.period, 
                multiplier=self.multiplier
            )
            
            # Aggiungi le colonne del Supertrend al DataFrame
            trend_col = f'SUPERTd_{self.period}_{self.multiplier}'
            value_col = f'SUPERT_{self.period}_{self.multiplier}'
            
            df_working['Supertrend_Value'] = supertrend[value_col]
            df_working['Supertrend_Trend'] = supertrend[trend_col]
            
        except Exception as e:
            print(f"Errore nel calcolo del Supertrend: {e}")
            return pd.DataFrame()

        # --- Generazione dei Segnali ---
        df_working['Signal'] = 0  # Inizializza la colonna Signal
        df_working['Position'] = 0  # Inizializza la colonna Position

        # Rimuovi le righe con NaN risultanti dal calcolo del Supertrend
        df_working.dropna(subset=['Supertrend_Value', 'Supertrend_Trend'], inplace=True)
        
        if df_working.empty:
            print("Avviso: DataFrame vuoto dopo la rimozione dei NaN degli indicatori per Supertrend.")
            return pd.DataFrame()

        # Itera sul DataFrame per determinare i segnali
        for i in range(1, len(df_working)):
            prev_position = df_working['Position'].iloc[i-1]
            current_trend = df_working['Supertrend_Trend'].iloc[i]
            prev_trend = df_working['Supertrend_Trend'].iloc[i-1]

            # Determina le condizioni di trading
            # Cambio da trend ribassista a rialzista (da -1 a 1)
            uptrend_start = (prev_trend == -1) and (current_trend == 1)
            
            # Cambio da trend rialzista a ribassista (da 1 a -1)
            downtrend_start = (prev_trend == 1) and (current_trend == -1)

            # Logica per aggiornare la posizione e generare i segnali
            if prev_position == 0:  # Se eravamo flat
                if uptrend_start:
                    df_working.loc[df_working.index[i], 'Signal'] = 1  # Segnale BUY
                    df_working.loc[df_working.index[i], 'Position'] = 1  # Passa a long
                elif downtrend_start:
                    df_working.loc[df_working.index[i], 'Signal'] = -1  # Segnale SELL
                    df_working.loc[df_working.index[i], 'Position'] = -1  # Passa a short
                else:
                    df_working.loc[df_working.index[i], 'Position'] = 0  # Rimane flat

            elif prev_position == 1:  # Se eravamo long
                if downtrend_start:
                    df_working.loc[df_working.index[i], 'Signal'] = -1  # Segnale SELL (per chiudere long e aprire short)
                    df_working.loc[df_working.index[i], 'Position'] = -1  # Passa a short
                else:
                    df_working.loc[df_working.index[i], 'Position'] = 1  # Rimane long

            elif prev_position == -1:  # Se eravamo short
                if uptrend_start:
                    df_working.loc[df_working.index[i], 'Signal'] = 1  # Segnale BUY (per chiudere short e aprire long)
                    df_working.loc[df_working.index[i], 'Position'] = 1  # Passa a long
                else:
                    df_working.loc[df_working.index[i], 'Position'] = -1  # Rimane short

        # Converte 'Signal' e 'Position' in int per consistenza
        df_working['Signal'] = df_working['Signal'].astype(int)
        df_working['Position'] = df_working['Position'].astype(int)

        self.processed_df = df_working
        return self.processed_df
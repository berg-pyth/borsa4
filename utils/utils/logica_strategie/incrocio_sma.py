# BorsaNew_app/utils/logica_strategie/incrocio_sma.py

import pandas as pd
import pandas_ta as ta

class IncrocioSmaStrategy: # <-- NOME DELLA CLASSE: sarà usato in strategies_config.py
    """
    Implementa la strategia di trading basata sull'incrocio di due Medie Mobili Semplici (SMA).
    """
    
    @staticmethod
    def get_strategy_parameters():
        """
        Restituisce i parametri configurabili della strategia.
        
        Returns:
            dict: Dizionario con i parametri della strategia e le loro configurazioni.
        """
        return {
            "short_sma_length": {
                "type": "int", 
                "default": 10, 
                "min_value": 5, 
                "max_value": 30, 
                "step": 1, 
                "label": "SMA Veloce"
            },
            "long_sma_length": {
                "type": "int", 
                "default": 50, 
                "min_value": 20, 
                "max_value": 100, 
                "step": 5, 
                "label": "SMA Lenta"
            }
        }
    def __init__(self, df: pd.DataFrame, short_sma_length: int, long_sma_length: int):
        """
        Inizializza la strategia con i dati e i parametri.

        Args:
            df (pd.DataFrame): DataFrame di input con dati OHLCV (colonne 'Open', 'High', 'Low', 'Close', 'Volume').
            short_sma_length (int): Periodo per la SMA veloce.
            long_sma_length (int): Periodo per la SMA lenta.
        """
        self.df = df.copy() # Lavora su una copia del DataFrame originale
        self.short_sma_length = short_sma_length
        self.long_sma_length = long_sma_length
        self.processed_df = None

        # Validazione dei parametri
        if self.short_sma_length >= self.long_sma_length:
            raise ValueError("La lunghezza della SMA veloce deve essere minore di quella della SMA lenta.")

    def generate_signals(self) -> pd.DataFrame:
        """
        Calcola gli indicatori (SMA) e genera i segnali di trading
        basati sull'incrocio delle medie mobili.

        Returns:
            pd.DataFrame: DataFrame originale con l'aggiunta delle colonne degli indicatori
                          e della colonna 'Signal' (1 per Buy, -1 per Sell, 0 per Hold).
                          Restituisce un DataFrame vuoto se i calcoli non sono possibili
                          o i dati insufficienti.
        """
        df_working = self.df.copy()

        # --- Pulizia e Normalizzazione Dati ---
        df_working.columns = [col.upper() for col in df_working.columns]

        required_cols = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
        if not all(col in df_working.columns for col in required_cols):
            print(f"Errore: DataFrame mancante di colonne OHLCV essenziali per Incrocio SMA. Richieste: {required_cols}")
            return pd.DataFrame()

        # --- Calcolo degli Indicatori ---
        try:
            df_working['SMA_Short'] = ta.sma(df_working['CLOSE'], length=self.short_sma_length)
            df_working['SMA_Long'] = ta.sma(df_working['CLOSE'], length=self.long_sma_length)
        except Exception as e:
            print(f"Errore nel calcolo delle SMA per Incrocio Medie Mobili: {e}")
            return pd.DataFrame()

        # --- Generazione dei Segnali ---
        df_working['Signal'] = 0 # Inizializza la colonna Signal
        df_working['Position'] = 0 # Inizializza la colonna Position

        # Rimuovi le righe con NaN risultanti dai calcoli delle SMA
        df_working.dropna(subset=['SMA_Short', 'SMA_Long'], inplace=True)
        
        if df_working.empty:
            print("Avviso: DataFrame vuoto dopo la rimozione dei NaN degli indicatori per Incrocio SMA.")
            return pd.DataFrame()

        # Itera sul DataFrame per determinare i segnali
        for i in range(1, len(df_working)):
            prev_position = df_working['Position'].iloc[i-1]
            current_sma_short = df_working['SMA_Short'].iloc[i]
            current_sma_long = df_working['SMA_Long'].iloc[i]
            prev_sma_short = df_working['SMA_Short'].iloc[i-1]
            prev_sma_long = df_working['SMA_Long'].iloc[i-1]

            # Determina le condizioni di trading
            long_condition = (prev_sma_short < prev_sma_long) and (current_sma_short > current_sma_long)
            short_condition = (prev_sma_short > prev_sma_long) and (current_sma_short < current_sma_long)

            # Logica per aggiornare la posizione e generare i segnali
            if prev_position == 0:  # Se eravamo flat
                if long_condition:
                    df_working.loc[df_working.index[i], 'Signal'] = 1  # Segnale BUY
                    df_working.loc[df_working.index[i], 'Position'] = 1  # Passa a long
                elif short_condition:
                    df_working.loc[df_working.index[i], 'Signal'] = -1  # Segnale SELL
                    df_working.loc[df_working.index[i], 'Position'] = -1  # Passa a short
                else:
                    df_working.loc[df_working.index[i], 'Position'] = 0  # Rimane flat

            elif prev_position == 1:  # Se eravamo long
                if short_condition:  # Priorità all'inversione esplicita
                    df_working.loc[df_working.index[i], 'Signal'] = -1  # Segnale SELL (per chiudere long e aprire short)
                    df_working.loc[df_working.index[i], 'Position'] = -1  # Passa a short
                elif current_sma_short < current_sma_long:  # Se la condizione long non è più vera
                    df_working.loc[df_working.index[i], 'Signal'] = -1  # Segnale SELL (per chiudere long)
                    df_working.loc[df_working.index[i], 'Position'] = 0  # Passa a flat
                else:
                    df_working.loc[df_working.index[i], 'Position'] = 1  # Rimane long

            elif prev_position == -1:  # Se eravamo short
                if long_condition:  # Priorità all'inversione esplicita
                    df_working.loc[df_working.index[i], 'Signal'] = 1  # Segnale BUY (per chiudere short e aprire long)
                    df_working.loc[df_working.index[i], 'Position'] = 1  # Passa a long
                elif current_sma_short > current_sma_long:  # Se la condizione short non è più vera
                    df_working.loc[df_working.index[i], 'Signal'] = 1  # Segnale BUY (per chiudere short)
                    df_working.loc[df_working.index[i], 'Position'] = 0  # Passa a flat
                else:
                    df_working.loc[df_working.index[i], 'Position'] = -1  # Rimane short

        # Converte 'Signal' e 'Position' in int per consistenza
        df_working['Signal'] = df_working['Signal'].astype(int)
        df_working['Position'] = df_working['Position'].astype(int)

        self.processed_df = df_working
        return self.processed_df

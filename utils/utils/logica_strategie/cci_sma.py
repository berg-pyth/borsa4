# BorsaNew_app/utils/logica_strategie/cci_sma.py

from ..numpy_compat import *
import pandas as pd
import numpy as np
import pandas_ta as ta

class CciSmaStrategy:
    """
    Implementa la strategia di trading CCI-SMA.
    Incapsula la logica di calcolo degli indicatori e generazione dei segnali.
    I segnali (1 per Buy, -1 per Sell) vengono generati solo quando si verifica
    un'azione di trading (ingresso o uscita da una posizione desiderata).
    """
    
    @staticmethod
    def get_strategy_parameters():
        """
        Restituisce i parametri configurabili della strategia.
        
        Returns:
            dict: Dizionario con i parametri della strategia e le loro configurazioni.
        """
        return {
            "cci_length": {
                "type": "int", 
                "default": 14, 
                "min_value": 5, 
                "max_value": 30, 
                "step": 1, 
                "label": "Lunghezza CCI"
            },
            "sma_length": {
                "type": "int", 
                "default": 20, 
                "min_value": 10, 
                "max_value": 50, 
                "step": 5, 
                "label": "Lunghezza SMA"
            }
        }
    def __init__(self, df: pd.DataFrame, cci_length: int, sma_length: int):
        """
        Inizializza la strategia con i dati e i parametri.

        Args:
            df (pd.DataFrame): DataFrame di input con dati OHLCV (colonne 'Open', 'High', 'Low', 'Close', 'Volume').
            cci_length (int): Periodo per il calcolo del CCI.
            sma_length (int): Periodo per il calcolo della SMA.
        """
        self.df = df.copy()
        
        # Verifica che i parametri siano validi
        if cci_length <= 0:
            print(f"Errore: cci_length deve essere positivo, valore ricevuto: {cci_length}")
            cci_length = 14  # Usa un valore predefinito
        
        if sma_length <= 0:
            print(f"Errore: sma_length deve essere positivo, valore ricevuto: {sma_length}")
            sma_length = 20  # Usa un valore predefinito
            
        self.cci_length = cci_length
        self.sma_length = sma_length
        self.processed_df = None

    def generate_signals(self) -> pd.DataFrame:
        """
        Calcola gli indicatori e genera i segnali di trading per la strategia CCI-SMA.
        I segnali (1 per Buy, -1 per Sell) vengono generati solo quando si verifica
        un'azione di trading (ingresso o uscita da una posizione desiderata).

        Returns:
            pd.DataFrame: DataFrame originale con l'aggiunta delle colonne degli indicatori
                          e della colonna 'Signal' e 'Position'. Restituisce un DataFrame
                          vuoto se i calcoli non sono possibili o i dati insufficienti.
        """
        df_working = self.df.copy()

        # --- Pulizia e Normalizzazione Dati ---
        new_columns = []
        for col in df_working.columns:
            if isinstance(col, tuple):
                new_columns.append(str(col[0]).upper())
            else:
                new_columns.append(str(col).upper())
        df_working.columns = new_columns

        # Stampa le colonne disponibili per debug
        print(f"Colonne disponibili nel DataFrame: {df_working.columns.tolist()}")
        
        # Verifica se le colonne sono in formato misto (alcune maiuscole, alcune minuscole)
        mixed_case_cols = {col.upper(): col for col in df_working.columns if col.upper() != col}
        if mixed_case_cols:
            print(f"Avviso: Colonne con formato misto rilevate: {mixed_case_cols}")
            # Rinomina le colonne in formato misto
            for upper_col, original_col in mixed_case_cols.items():
                df_working.rename(columns={original_col: upper_col}, inplace=True)
        
        required_cols = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
        missing_cols = [col for col in required_cols if col not in df_working.columns]
        if missing_cols:
            print(f"Errore: DataFrame mancante di colonne OHLCV essenziali. Mancanti: {missing_cols}")
            print(f"Colonne disponibili: {df_working.columns.tolist()}")
            return pd.DataFrame()

        # --- Calcolo degli Indicatori ---
        try:
            # Verifica che le colonne necessarie esistano e non contengano valori nulli
            if 'HIGH' not in df_working.columns or 'LOW' not in df_working.columns or 'CLOSE' not in df_working.columns:
                print(f"Errore: Colonne necessarie mancanti. Colonne disponibili: {df_working.columns.tolist()}")
                return pd.DataFrame()
                
            # Verifica che non ci siano valori nulli nelle colonne necessarie
            if df_working['HIGH'].isnull().any() or df_working['LOW'].isnull().any() or df_working['CLOSE'].isnull().any():
                print("Errore: Valori nulli trovati nelle colonne HIGH, LOW o CLOSE")
                return pd.DataFrame()
                
            # Calcola gli indicatori
            df_working['CCI'] = ta.cci(df_working['HIGH'], df_working['LOW'], df_working['CLOSE'], length=self.cci_length)
            df_working['SMA'] = ta.sma(df_working['CLOSE'], length=self.sma_length)
        except Exception as e:
            print(f"Errore nel calcolo degli indicatori per CCI-SMA: {e}")
            return pd.DataFrame()

        # --- Generazione dei Segnali e Gestione della Posizione (simulata) ---
        df_working.dropna(subset=['CCI', 'SMA'], inplace=True)
        
        if df_working.empty:
            print("Avviso: DataFrame vuoto dopo la rimozione dei NaN degli indicatori per CCI-SMA.")
            return pd.DataFrame()

        # Inizializza la colonna 'Signal' a 0 per default
        df_working['Signal'] = 0
        # Inizializza una colonna temporanea per la posizione simulata
        df_working['simulated_position'] = 0 # 0: flat, 1: long, -1: short

        # Flags per tenere traccia dello stato delle condizioni
        df_working['long_condition_met'] = (df_working['CCI'] > 0) & (df_working['CLOSE'] > df_working['SMA'])
        df_working['short_condition_met'] = (df_working['CCI'] < 0) & (df_working['CLOSE'] < df_working['SMA'])

        # Itera sul DataFrame per determinare i segnali basati sulla posizione simulata
        for i in range(1, len(df_working)):
            prev_simulated_position = df_working['simulated_position'].iloc[i-1]
            long_condition_today = df_working['long_condition_met'].iloc[i]
            short_condition_today = df_working['short_condition_met'].iloc[i]

            # Logica per aggiornare la posizione simulata e generare i segnali
            if prev_simulated_position == 0: # Se eravamo flat
                if long_condition_today:
                    df_working.loc[df_working.index[i], 'Signal'] = 1 # Segnale BUY
                    df_working.loc[df_working.index[i], 'simulated_position'] = 1 # Passa a long
                elif short_condition_today:
                    df_working.loc[df_working.index[i], 'Signal'] = -1 # Segnale SELL
                    df_working.loc[df_working.index[i], 'simulated_position'] = -1 # Passa a short
                else:
                    df_working.loc[df_working.index[i], 'simulated_position'] = 0 # Rimane flat
            
            elif prev_simulated_position == 1: # Se eravamo long
                # Se le condizioni di vendita sono soddisfatte, o le condizioni di acquisto non sono più valide
                if short_condition_today: # Priorità all'inversione esplicita
                    df_working.loc[df_working.index[i], 'Signal'] = -1 # Segnale SELL (per chiudere long e aprire short)
                    df_working.loc[df_working.index[i], 'simulated_position'] = -1 # Passa a short
                elif not long_condition_today: # Se la condizione long non è più vera, chiudi long
                    df_working.loc[df_working.index[i], 'Signal'] = -1 # Segnale SELL (per chiudere long)
                    df_working.loc[df_working.index[i], 'simulated_position'] = 0 # Passa a flat
                else:
                    df_working.loc[df_working.index[i], 'simulated_position'] = 1 # Rimane long
            
            elif prev_simulated_position == -1: # Se eravamo short
                # Se le condizioni di acquisto sono soddisfatte, o le condizioni di vendita non sono più valide
                if long_condition_today: # Priorità all'inversione esplicita
                    df_working.loc[df_working.index[i], 'Signal'] = 1 # Segnale BUY (per chiudere short e aprire long)
                    df_working.loc[df_working.index[i], 'simulated_position'] = 1 # Passa a long
                elif not short_condition_today: # Se la condizione short non è più vera, chiudi short
                    df_working.loc[df_working.index[i], 'Signal'] = 1 # Segnale BUY (per chiudere short)
                    df_working.loc[df_working.index[i], 'simulated_position'] = 0 # Passa a flat
                else:
                    df_working.loc[df_working.index[i], 'simulated_position'] = -1 # Rimane short

        # Converte 'Signal' in int per consistenza
        df_working['Signal'] = df_working['Signal'].astype(int)
        # Converte 'simulated_position' in int e la rinomina in 'Position'
        df_working['Position'] = df_working['simulated_position'].astype(int)

        # Rimuovi le colonne temporanee (tranne 'simulated_position' che ora è 'Position')
        self.processed_df = df_working.drop(columns=['simulated_position', 'long_condition_met', 'short_condition_met'], errors='ignore')
        return self.processed_df

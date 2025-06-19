# BorsaNew_app/utils/logica_strategie/livelli_stocastico.py

import pandas as pd
import pandas_ta as ta

class LivelliStocasticoStrategy: # <-- NOME DELLA CLASSE: sarà usato in strategies_config.py
    """
    Implementa la strategia basata sull'Oscillatore Stocastico.
    Genera segnali basati sul superamento di livelli di soglia e crossover
    tra %D e la sua media mobile (%DD).
    """
    
    @staticmethod
    def get_strategy_parameters():
        """
        Restituisce i parametri configurabili della strategia.
        
        Returns:
            dict: Dizionario con i parametri della strategia e le loro configurazioni.
        """
        return {
            "periodo_k": {
                "type": "int", 
                "default": 14, 
                "min_value": 1, 
                "max_value": 50, 
                "step": 1, 
                "label": "Periodo %K"
            },
            "periodo_d": {
                "type": "int", 
                "default": 3, 
                "min_value": 1, 
                "max_value": 20, 
                "step": 1, 
                "label": "Periodo %D"
            },
            "periodo_dd": {
                "type": "int", 
                "default": 3, 
                "min_value": 1, 
                "max_value": 20, 
                "step": 1, 
                "label": "Periodo %DD"
            },
            "soglia_buy": {
                "type": "int", 
                "default": 20, 
                "min_value": 10, 
                "max_value": 50, 
                "step": 5, 
                "label": "Soglia Buy"
            },
            "soglia_sell": {
                "type": "int", 
                "default": 80, 
                "min_value": 50, 
                "max_value": 90, 
                "step": 5, 
                "label": "Soglia Sell"
            }
        }
    def __init__(self, df: pd.DataFrame, periodo_k: int, periodo_d: int, periodo_dd: int, soglia_buy: int, soglia_sell: int):
        """
        Inizializza la strategia con i dati e i parametri specifici per lo Stocastico.

        Args:
            df (pd.DataFrame): DataFrame di input con dati OHLCV.
            periodo_k (int): Periodo per il calcolo di %K.
            periodo_d (int): Periodo per il calcolo di %D (SMA di %K).
            periodo_dd (int): Periodo per il calcolo di %DD (SMA di %D).
            soglia_buy (int): Livello sotto il quale si cerca un segnale di acquisto.
            soglia_sell (int): Livello sopra il quale si cerca un segnale di vendita.
        """
        self.df = df.copy()
        self.periodo_k = periodo_k
        self.periodo_d = periodo_d
        self.periodo_dd = periodo_dd # Questa è la media mobile di %D
        self.soglia_buy = soglia_buy
        self.soglia_sell = soglia_sell
        self.processed_df = None

        # Validazione basilare dei parametri
        if not (1 <= self.periodo_k <= 50 and 1 <= self.periodo_d <= 20 and 1 <= self.periodo_dd <= 20):
            raise ValueError("I periodi per Stocastico devono essere validi (es. K:1-50, D:1-20, DD:1-20).")
        if not (10 <= self.soglia_buy < self.soglia_sell <= 90):
            raise ValueError("Le soglie buy/sell devono essere valide (Buy < Sell, Buy>=10, Sell<=90).")


    def generate_signals(self) -> pd.DataFrame:
        """
        Calcola l'Oscillatore Stocastico e genera i segnali di trading.

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
            print(f"Errore: DataFrame mancante di colonne OHLCV essenziali per Stocastico. Richieste: {required_cols}")
            return pd.DataFrame()

        # --- Calcolo degli Indicatori ---
        try:
            # Calcola l'Oscillatore Stocastico con %K e %D
            # pandas_ta restituisce un DataFrame con colonne tipo STOCHk_14_3_3 e STOCHd_14_3_3
            stoch_data = ta.stoch(
                high=df_working['HIGH'],
                low=df_working['LOW'],
                close=df_working['CLOSE'],
                k=self.periodo_k,
                d=self.periodo_d,
                append=False
            )
            # Rinomina per facilità d'uso
            k_col = [col for col in stoch_data.columns if 'STOCHk' in col][0]
            d_col = [col for col in stoch_data.columns if 'STOCHd' in col][0]
            
            df_working['%K'] = stoch_data[k_col]
            df_working['%D'] = stoch_data[d_col]

            # Calcola %DD (media mobile di %D)
            df_working['%DD'] = ta.sma(df_working['%D'], length=self.periodo_dd)

        except Exception as e:
            print(f"Errore nel calcolo degli indicatori Stocastico: {e}")
            return pd.DataFrame()

        # --- Generazione dei Segnali ---
        df_working['Signal'] = 0 # Inizializza la colonna Signal

        # Rimuovi le righe con NaN risultanti dagli indicatori
        df_working.dropna(subset=['%K', '%D', '%DD'], inplace=True)
        
        if df_working.empty:
            print("Avviso: DataFrame vuoto dopo la rimozione dei NaN degli indicatori per Stocastico.")
            return pd.DataFrame()

        # Logica di trading per lo Stocastico
        # Si basa sul crossover di %D e %DD e sul superamento delle soglie

        # Condizione BUY: %D incrocia sopra %DD E %D è sotto la soglia di BUY
        df_working.loc[
            (df_working['%D'].shift(1) < df_working['%DD'].shift(1)) & # %D era sotto %DD
            (df_working['%D'] > df_working['%DD']) &                   # %D ora è sopra %DD
            (df_working['%D'] < self.soglia_buy),                      # E %D è sotto la soglia di BUY
            'Signal'
        ] = 1

        # Condizione SELL: %D incrocia sotto %DD E %D è sopra la soglia di SELL
        df_working.loc[
            (df_working['%D'].shift(1) > df_working['%DD'].shift(1)) & # %D era sopra %DD
            (df_working['%D'] < df_working['%DD']) &                   # %D ora è sotto %DD
            (df_working['%D'] > self.soglia_sell),                     # E %D è sopra la soglia di SELL
            'Signal'
        ] = -1

        df_working['Signal'] = df_working['Signal'].astype(int)

        self.processed_df = df_working
        return self.processed_df

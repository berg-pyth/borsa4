#livelli di bollinger

import pandas as pd
import numpy as np
import pandas_ta as ta # Utilizziamo la libreria pandas_ta per calcolare le Bande di Bollinger

# Definizione della strategia basata sui crossover del prezzo di chiusura con le Bande di Bollinger.

class LivelliBollingerStrategy:
    def __init__(self, df: pd.DataFrame = None, length: int = 20, std: float = 2.0):
        self.df = df
        self.length = length
        self.std = std
        self.indicator_cols = []

    def generate_signals(self) -> pd.DataFrame:
        """
        Genera segnali di trading basati sulla strategia dei crossover del prezzo di chiusura
        con le Bande di Bollinger.

        La logica dei segnali è:
        - Entrata LONG: quando il prezzo di chiusura rompe dal basso verso l'alto la Banda di Bollinger inferiore.
        - Uscita LONG: quando il prezzo di chiusura rompe verso il basso la Banda di Bollinger superiore,
          o se il prezzo di chiusura rompe verso il basso la media mobile interna (Middle Band).
        - Entrata SHORT: quando il prezzo di chiusura rompe verso il basso la Banda di Bollinger superiore.
        - Uscita SHORT: quando il prezzo di chiusura rompe dal basso verso l'alto la Banda di Bollinger inferiore,
          o se il prezzo di chiusura rompe verso l'alto la media mobile interna (Middle Band).

        Returns:
            pd.DataFrame: DataFrame originale con l'aggiunta delle colonne
                         degli indicatori (Bande di Bollinger) e dei segnali ('Signal').
                         La colonna 'Signal' contiene:
                         1 per segnale di entrata LONG
                         -1 per segnale di entrata SHORT
                         0 per nessun segnale o uscita
        """
        if self.df is None:
            print("Errore: DataFrame non fornito.")
            return pd.DataFrame()

        # Crea una copia del DataFrame per lavorarci
        df_working = self.df.copy()

        # Normalizza i nomi delle colonne in maiuscolo
        df_working.columns = [col.upper() for col in df_working.columns]

        # Verifica le colonne richieste
        required_cols = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
        if not all(col in df_working.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df_working.columns]
            print(f"Errore: DataFrame mancante di colonne OHLCV essenziali. Mancanti: {missing}")
            return pd.DataFrame()

        try:
            # Calcola le Bande di Bollinger utilizzando pandas_ta
            # Usa il metodo bbands() che restituisce un DataFrame con le bande
            bbands = ta.bbands(
                close=df_working['CLOSE'],
                length=self.length,
                std=self.std
            )

            # Aggiungi le colonne delle bande al DataFrame di lavoro
            df_working['BBL'] = bbands['BBL_' + str(self.length) + '_' + str(self.std)]
            df_working['BBM'] = bbands['BBM_' + str(self.length) + '_' + str(self.std)]
            df_working['BBU'] = bbands['BBU_' + str(self.length) + '_' + str(self.std)]

            # Salva i nomi delle colonne degli indicatori
            self.indicator_cols = ['BBL', 'BBM', 'BBU']

            # Inizializza la colonna dei segnali a 0
            df_working['Signal'] = 0

            # Inizializza una colonna temporanea per la posizione simulata
            df_working['simulated_position'] = 0  # 0: flat, 1: long, -1: short

            # Itera sul DataFrame per determinare i segnali basati sulla posizione simulata
            for i in range(1, len(df_working)):
                prev_simulated_position = df_working['simulated_position'].iloc[i-1]
                current_close = df_working['CLOSE'].iloc[i]
                current_bbu = df_working['BBU'].iloc[i]
                current_bbl = df_working['BBL'].iloc[i]
                current_bbm = df_working['BBM'].iloc[i]
                
                # Logica per aggiornare la posizione simulata e generare i segnali
                if prev_simulated_position == 0:  # Se eravamo flat
                    if current_close > current_bbl and df_working['CLOSE'].iloc[i-1] <= df_working['BBL'].iloc[i-1]:
                        df_working.loc[df_working.index[i], 'Signal'] = 1  # Segnale BUY
                        df_working.loc[df_working.index[i], 'simulated_position'] = 1  # Passa a long
                    elif current_close < current_bbu and df_working['CLOSE'].iloc[i-1] >= df_working['BBU'].iloc[i-1]:
                        df_working.loc[df_working.index[i], 'Signal'] = -1  # Segnale SELL
                        df_working.loc[df_working.index[i], 'simulated_position'] = -1  # Passa a short
                
                elif prev_simulated_position == 1:  # Se eravamo long
                    if current_close < current_bbu and df_working['CLOSE'].iloc[i-1] >= df_working['BBU'].iloc[i-1]:
                        df_working.loc[df_working.index[i], 'Signal'] = -1  # Segnale SELL (per chiudere long)
                        df_working.loc[df_working.index[i], 'simulated_position'] = 0  # Passa a flat
                    elif current_close < current_bbm and df_working['CLOSE'].iloc[i-1] >= df_working['BBM'].iloc[i-1]:
                        df_working.loc[df_working.index[i], 'Signal'] = -1  # Segnale SELL (per chiudere long)
                        df_working.loc[df_working.index[i], 'simulated_position'] = 0  # Passa a flat
                
                elif prev_simulated_position == -1:  # Se eravamo short
                    if current_close > current_bbl and df_working['CLOSE'].iloc[i-1] <= df_working['BBL'].iloc[i-1]:
                        df_working.loc[df_working.index[i], 'Signal'] = 1  # Segnale BUY (per chiudere short)
                        df_working.loc[df_working.index[i], 'simulated_position'] = 0  # Passa a flat
                    elif current_close > current_bbm and df_working['CLOSE'].iloc[i-1] <= df_working['BBM'].iloc[i-1]:
                        df_working.loc[df_working.index[i], 'Signal'] = 1  # Segnale BUY (per chiudere short)
                        df_working.loc[df_working.index[i], 'simulated_position'] = 0  # Passa a flat

            # Converte 'Signal' in int per consistenza
            df_working['Signal'] = df_working['Signal'].astype(int)
            # Converte 'simulated_position' in int e la rinomina in 'Position'
            df_working['Position'] = df_working['simulated_position'].astype(int)

            # Rimuovi le colonne temporanee
            df_working = df_working.drop(columns=['simulated_position'], errors='ignore')

            # Aggiorna il DataFrame originale con i risultati
            self.df = df_working

            return self.df

        except Exception as e:
            print(f"Errore nel calcolo delle Bande di Bollinger: {str(e)}")
            return pd.DataFrame()

    def get_indicator_columns(self) -> list:
        """
        Restituisce la lista delle colonne degli indicatori utilizzate dalla strategia.
        """
        return self.indicator_cols

    @staticmethod
    def get_strategy_parameters() -> dict:
        """
        Restituisce un dizionario che definisce i parametri configurabili
        della strategia Bande di Bollinger.
        """
        return {
            'length': {
                'label': 'Periodo Media Mobile (Middle Band)',
                'type': 'number',
                'default': 20,
                'min_value': 1,
                'step': 1,
                'format': '%d'
            },
            'std': {
                'label': 'Moltiplicatore Deviazione Standard',
                'type': 'number',
                'default': 2.0,
                'min_value': 0.1,
                'step': 0.1,
                'format': '%.1f'
            }
        }

# --- Esempio di utilizzo (per test locale) ---
# if __name__ == '__main__':
#     print("Esecuzione test locale della strategia Bande di Bollinger...")
#     # Crea dati fittizi per il test
#     dates = pd.date_range(start='2020-01-01', periods=200, freq='D')
#     data_test = pd.DataFrame({
#         'Open': np.random.rand(200)*10 + 100,
#         'High': np.random.rand(200)*10 + 105,
#         'Low': np.random.rand(200)*10 + 95,
#         'Close': np.random.rand(200)*10 + 100,
#         'Volume': np.random.rand(200) * 100000
#     }, index=dates)
#
#     # Aggiungi un trend per rendere i dati più realistici
#     data_test['Close'] = data_test['Close'].cumsum() + 100
#     data_test['Open'] = data_test['Close'].shift(1)
#     data_test['High'] = data_test[['Open', 'Close']].max(axis=1) + np.random.rand(200)*5
#     data_test['Low'] = data_test[['Open', 'Close']].min(axis=1) - np.random.rand(200)*5
#     data_test = data_test.dropna() # Rimuovi la prima riga con NaN
#
#     print("Dati di test:")
#     print(data_test.head())
#
#     # Esegui la generazione dei segnali
#     dati_con_segnali = generate_signals(data_test.copy(), length=20, std=2.0)
#
#     print("\nDati con segnali e indicatori (ultime 10 righe):")
#     print(dati_con_segnali.tail(10))
#
#     print("\nColonne indicatori:")
#     print(get_indicator_columns(dati_con_segnali))
#
#     # Puoi visualizzare il grafico se hai le funzioni di plotting disponibili
#     # Ad esempio, se hai una funzione plot_strategy_signals(dati, indicator_cols):
#     # try:
#     #     from utils.plotting_utils import plot_strategy_signals
#     #     plot_strategy_signals(dati_con_segnali, get_indicator_columns(dati_con_segnali))
#     # except ImportError:
#     #     print("\nFunzione di plotting non trovata. Salta la visualizzazione del grafico.")
# Borsa2_app/utils/calcolo_indicatori/stocastico.py

import pandas as pd
import pandas_ta as ta

def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int, d_period: int) -> pd.DataFrame:
    """
    Calcola l'Oscillatore Stocastico (%K e %D) usando pandas_ta.

    Args:
        high (pd.Series): Serie dei prezzi massimi.
        low (pd.Series): Serie dei prezzi minimi.
        close (pd.Series): Serie dei prezzi di chiusura.
        k_period (int): Periodo per il calcolo di %K.
        d_period (int): Periodo per il calcolo di %D (SMA di %K).

    Returns:
        pd.DataFrame: DataFrame contenente le serie %K e %D.
                      Le colonne saranno nominate es. 'STOCHk_14_3_3' e 'STOCHd_14_3_3'.
    """
    if not all(isinstance(s, pd.Series) for s in [high, low, close]):
        raise TypeError("Inputs high, low, close must be pandas Series.")
    if not all(isinstance(p, int) and p > 0 for p in [k_period, d_period]):
        raise ValueError("Inputs k_period and d_period must be positive integers.")

    # pandas_ta restituisce un DataFrame per gli indicatori multi-output
    stoch_data = ta.stoch(high=high, low=low, close=close, k=k_period, d=d_period, append=False)
    # Rinomina le colonne per facilitare l'accesso in Streamlit
    # Le colonne di default sono tipo STOCHk_14_3_3 e STOCHd_14_3_3.
    # Le semplifichiamo a %K e %D o simili per il plotting e la tabella.
    # Troviamo i nomi generati da pandas_ta
    k_col = [col for col in stoch_data.columns if 'STOCHk' in col][0]
    d_col = [col for col in stoch_data.columns if 'STOCHd' in col][0]

    stoch_data = stoch_data.rename(columns={k_col: f"Stoch_%K_{k_period}_{d_period}", d_col: f"Stoch_%D_{k_period}_{d_period}"})
    return stoch_data
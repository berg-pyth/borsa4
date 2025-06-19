# Borsa2_app/utils/calcolo_indicatori/sma.py

import pandas as pd
import pandas_ta as ta

def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """
    Calcola la Simple Moving Average (SMA) usando pandas_ta.

    Args:
        data (pd.Series): Serie di dati (solitamente prezzi di chiusura).
        period (int): Periodo per il calcolo della SMA.

    Returns:
        pd.Series: Serie contenente i valori della SMA.
    """
    if not isinstance(data, pd.Series):
        raise TypeError("Input 'data' must be a pandas Series.")
    if not isinstance(period, int) or period <= 0:
        raise ValueError("Input 'period' must be a positive integer.")

    # pandas_ta aggiunge l'indicatore direttamente al DataFrame/Series
    # e lo restituisce.
    # df.ta.sma(close=data, length=period) sarebbe se avessi un DataFrame
    # con una colonna 'close'. Qui passiamo direttamente la Series.
    return ta.sma(data, length=period)
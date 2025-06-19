# Borsa2_app/utils/calcolo_indicatori/rsi.py

import pandas as pd
import pandas_ta as ta

def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    """
    Calcola il Relative Strength Index (RSI) usando pandas_ta.

    Args:
        data (pd.Series): Serie di dati (solitamente prezzi di chiusura).
        period (int): Periodo per il calcolo dell'RSI.

    Returns:
        pd.Series: Serie contenente i valori dell'RSI.
    """
    if not isinstance(data, pd.Series):
        raise TypeError("Input 'data' must be a pandas Series.")
    if not isinstance(period, int) or period <= 0:
        raise ValueError("Input 'period' must be a positive integer.")

    return ta.rsi(data, length=period)

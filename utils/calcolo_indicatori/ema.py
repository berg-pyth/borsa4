# Borsa2_app/utils/calcolo_indicatori/ema.py

import pandas as pd
import pandas_ta as ta

def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """
    Calcola l'Exponential Moving Average (EMA) usando pandas_ta.

    Args:
        data (pd.Series): Serie di dati (solitamente prezzi di chiusura).
        period (int): Periodo per il calcolo dell'EMA.

    Returns:
        pd.Series: Serie contenente i valori dell'EMA.
    """
    if not isinstance(data, pd.Series):
        raise TypeError("Input 'data' must be a pandas Series.")
    if not isinstance(period, int) or period <= 0:
        raise ValueError("Input 'period' must be a positive integer.")

    return ta.ema(data, length=period)


# Borsa2_app/utils/calcolo_indicatori/cci.py


import pandas as pd
import pandas_ta as ta

def calculate_cci(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 20) -> pd.Series:
    """
    Calcola l'Indice del Canale delle Materie Prime (CCI) usando pandas_ta.

    Args:
        high (pd.Series): Serie dei prezzi massimi (High).
        low (pd.Series): Serie dei prezzi minimi (Low).
        close (pd.Series): Serie dei prezzi di chiusura (Close).
        length (int): Periodo per il calcolo del CCI (default: 20).

    Returns:
        pd.Series: Serie contenente i valori del CCI.
    """
    if not isinstance(high, pd.Series) or not isinstance(low, pd.Series) or not isinstance(close, pd.Series):
        raise TypeError("Inputs high, low, close must be pandas Series.")
    if not isinstance(length, int) or length <= 0:
        raise ValueError("Input 'length' must be a positive integer.")

    # pandas_ta calcola il CCI direttamente. Restituisce una singola serie.
    # La colonna di default sarà tipo 'CCI_20'
    return ta.cci(high=high, low=low, close=close, length=length, append=False)
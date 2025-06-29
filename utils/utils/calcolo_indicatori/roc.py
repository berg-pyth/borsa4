# Borsa2_app/utils/calcolo_indicatori/roc.py

import pandas as pd
import pandas_ta as ta

def calculate_roc(close: pd.Series, length: int = 10) -> pd.Series:
    """
    Calcola il Rate of Change (ROC) usando pandas_ta.

    Args:
        close (pd.Series): Serie dei prezzi di chiusura (Close).
        length (int): Periodo per il calcolo del ROC (default: 10).

    Returns:
        pd.Series: Serie contenente i valori del ROC.
    """
    if not isinstance(close, pd.Series):
        raise TypeError("Input 'close' must be a pandas Series.")
    if not isinstance(length, int) or length <= 0:
        raise ValueError("Input 'length' must be a positive integer.")

    # pandas_ta calcola il ROC direttamente. Restituisce una singola serie.
    # La colonna di default sarà tipo 'ROC_10'
    return ta.roc(close=close, length=length, append=False)

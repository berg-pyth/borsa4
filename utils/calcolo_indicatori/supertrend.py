# Borsa2_app/utils/calcolo_indicatori/supertrend.py

from ..numpy_compat import *
import pandas as pd
import numpy as np
import pandas_ta as ta

def calculate_supertrend(high, low, close, period=10, multiplier=3.0):
    """
    Calcola l'indicatore Supertrend utilizzando pandas-ta.
    
    Parameters:
    -----------
    high : pandas.Series
        Serie dei prezzi massimi.
    low : pandas.Series
        Serie dei prezzi minimi.
    close : pandas.Series
        Serie dei prezzi di chiusura.
    period : int, default 10
        Periodo per il calcolo dell'ATR.
    multiplier : float, default 3.0
        Moltiplicatore per l'ATR.
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame contenente le colonne del Supertrend.
    """
    # Crea un DataFrame con i dati OHLC
    df = pd.DataFrame({
        'high': high,
        'low': low,
        'close': close
    })
    
    # Calcola il Supertrend usando pandas-ta
    supertrend = ta.supertrend(
        high=df['high'], 
        low=df['low'], 
        close=df['close'], 
        length=period, 
        multiplier=multiplier
    )
    
    # Rinomina le colonne per maggiore chiarezza
    if supertrend is not None:
        # Estrai le colonne rilevanti
        result = pd.DataFrame({
            'trend': supertrend[f'SUPERTd_{period}_{multiplier}'],
            'supertrend': supertrend[f'SUPERT_{period}_{multiplier}'],
            'up_trend': pd.Series(index=close.index),
            'down_trend': pd.Series(index=close.index)
        })
        
        # Crea le linee separate per trend rialzista e ribassista
        result.loc[result['trend'] == 1, 'up_trend'] = result.loc[result['trend'] == 1, 'supertrend']
        result.loc[result['trend'] != 1, 'down_trend'] = result.loc[result['trend'] != 1, 'supertrend']
        
        return result
    else:
        # Fallback in caso di errore con pandas-ta
        return pd.DataFrame({
            'trend': pd.Series(index=close.index),
            'supertrend': pd.Series(index=close.index),
            'up_trend': pd.Series(index=close.index),
            'down_trend': pd.Series(index=close.index)
        })
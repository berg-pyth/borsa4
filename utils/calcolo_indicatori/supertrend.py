# Borsa2_app/utils/calcolo_indicatori/supertrend.py

import pandas as pd
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
        for i in range(len(result)):
            if result['trend'].iloc[i] == 1:  # Trend rialzista
                result['up_trend'].iloc[i] = result['supertrend'].iloc[i]
                result['down_trend'].iloc[i] = None
            else:  # Trend ribassista
                result['up_trend'].iloc[i] = None
                result['down_trend'].iloc[i] = result['supertrend'].iloc[i]
        
        return result
    else:
        # Fallback in caso di errore con pandas-ta
        return pd.DataFrame({
            'trend': pd.Series(index=close.index),
            'supertrend': pd.Series(index=close.index),
            'up_trend': pd.Series(index=close.index),
            'down_trend': pd.Series(index=close.index)
        })
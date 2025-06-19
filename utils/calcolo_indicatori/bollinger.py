# Borsa2_app/utils/calcolo_indicatori/bollinger.py

import pandas as pd
import pandas_ta as ta

def calculate_bollinger_bands(data: pd.Series, length: int = 20, std: int = 2) -> pd.DataFrame:
    """
    Calcola le Bande di Bollinger (BBANDS) usando pandas_ta.

    Args:
        data (pd.Series): Serie di dati (solitamente prezzi di chiusura).
        length (int): Periodo per il calcolo della media mobile centrale (default: 20).
        std (int): Numero di deviazioni standard per le bande superiore e inferiore (default: 2).

    Returns:
        pd.DataFrame: DataFrame contenente le serie della banda inferiore, centrale e superiore.
                      Le colonne saranno nominate es. 'BBL_20_2.0', 'BBM_20_2.0', 'BBU_20_2.0'.
    """
    if not isinstance(data, pd.Series):
        raise TypeError("Input 'data' must be a pandas Series.")
    if not isinstance(length, int) or length <= 0:
        raise ValueError("Input 'length' must be a positive integer.")
    if not isinstance(std, (int, float)) or std <= 0:
        raise ValueError("Input 'std' must be a positive number.")

    # pandas_ta restituisce un DataFrame per gli indicatori multi-output
    # Le colonne di default saranno tipo BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
    bbands_data = ta.bbands(close=data, length=length, std=std, append=False)

    # Rinomina le colonne per facilitare l'accesso e la visualizzazione
    # Trova i nomi generati da pandas_ta per le bande inferiore, media e superiore
    lower_band_col = [col for col in bbands_data.columns if 'BBL_' in col][0]
    mid_band_col = [col for col in bbands_data.columns if 'BBM_' in col][0]
    upper_band_col = [col for col in bbands_data.columns if 'BBU_' in col][0]

    # Rinomina per chiarezza
    bbands_data = bbands_data.rename(columns={
        lower_band_col: f"BB_Lower_{length}_{std}",
        mid_band_col: f"BB_Middle_{length}_{std}",
        upper_band_col: f"BB_Upper_{length}_{std}"
    })

    return bbands_data

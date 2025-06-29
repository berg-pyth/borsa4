# Fix per compatibilità NumPy 2.0+
import numpy as np

if not hasattr(np, 'NaN'):
    np.NaN = np.nan
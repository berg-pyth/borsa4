# BorsaNew_app/utils/strategies_config.py

# Rimuovi le importazioni dirette delle funzioni
# from .logica_strategie import cci_sma
# from .logica_strategie import incrocio_sma
# from .logica_strategie import livelli_bollinger
# from .logica_strategie import livelli_stocastico

STRATEGIE_DISPONIBILI = {
    "CCI-SMA": {
        # Aggiornato per usare 'module' e 'class'
        "module": "cci_sma",  # Nome del file Python (senza .py)
        "class": "CciSmaStrategy", # Nome della classe che hai definito in cci_sma.py
        "description": "Strategia basata su incroci CCI e relazione prezzo/SMA.",
        "parameters": {
            "cci_length": {"type": "int", "default": 14, "min_value": 5, "max_value": 30, "step": 1, "label": "Lunghezza CCI"},
            "sma_length": {"type": "int", "default": 20, "min_value": 10, "max_value": 50, "step": 5, "label": "Lunghezza SMA"}
        }
    },
    "Incrocio Medie Mobili": {
        # Aggiornato per usare 'module' e 'class'
        "module": "incrocio_sma", # Nome del file Python (senza .py)
        "class": "IncrocioSmaStrategy", # Nome della classe che hai definito in incrocio_sma.py
        "description": "Strategia basata sull'incrocio di due medie mobili semplici.",
        "parameters": {
            "short_sma_length": {"type": "int", "default": 10, "min_value": 5, "max_value": 30, "step": 1, "label": "SMA Veloce"},
            "long_sma_length": {"type": "int", "default": 50, "min_value": 20, "max_value": 100, "step": 5, "label": "SMA Lenta"}
        }
    },
   "Livelli Bollinger Bands": {
        # Aggiornato per usare 'module' e 'class'
        "module": "livelli_bollinger", # Nome del file Python (senza .py)
        "class": "LivelliBollingerStrategy", # Nome della classe che hai definito in livelli_bollinger.py
        "description": "Strategia basata sul superamento delle bande di Bollinger.",
        "parameters": {
            "length": {"type": "int", "default": 20, "min_value": 10, "max_value": 50, "step": 1, "label": "Lunghezza Bollinger"},
            "std": {"type": "float", "default": 2.0, "min_value": 1.0, "max_value": 3.0, "step": 0.1, "label": "Deviazione Std."}
        }
    },
   "Livelli Stocastico (DIFF D-DD)": {
        # Aggiornato per usare 'module' e 'class'
        "module": "livelli_stocastico", # Nome del file Python (senza .py)
        "class": "LivelliStocasticoStrategy", # Nome della classe che hai definito in livelli_stocastico.py
        "description": "Strategia Stocastico basata sul crossover della differenza tra %D e la sua media mobile (%DD).",
        "parameters": {
            "periodo_k": {"type": "int", "default": 14, "min_value": 1, "max_value": 50, "step": 1, "label": "Periodo %K"},
            "periodo_d": {"type": "int", "default": 3, "min_value": 1, "max_value": 20, "step": 1, "label": "Periodo %D"},
            "periodo_dd": {"type": "int", "default": 3, "min_value": 1, "max_value": 20, "step": 1, "label": "Periodo %DD"},
            "soglia_buy": {"type": "int", "default": 20, "min_value": 10, "max_value": 50, "step": 5, "label": "Soglia Buy"},
            "soglia_sell": {"type": "int", "default": 80, "min_value": 50, "max_value": 90, "step": 5, "label": "Soglia Sell"}
        }
    },
    "Supertrend": {
        "module": "supertrend_strategy", # Nome del file Python (senza .py)
        "class": "SupertrendStrategy", # Nome della classe che hai definito in supertrend_strategy.py
        "description": "Strategia basata sull'indicatore Supertrend per identificare cambi di trend.",
        "parameters": {
            "period": {"type": "int", "default": 10, "min_value": 5, "max_value": 30, "step": 1, "label": "Periodo ATR"},
            "multiplier": {"type": "float", "default": 3.0, "min_value": 1.0, "max_value": 6.0, "step": 0.1, "label": "Moltiplicatore"}
        }
    },
}
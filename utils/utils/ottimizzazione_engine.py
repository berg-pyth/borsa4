# ottimizzazione delle strategie

import pandas as pd
import numpy as np
import itertools # Utile per la grid search
import time # Per misurare il tempo di esecuzione (opzionale)
import importlib # Per importare moduli dinamicamente
import math # Per gestire i valori NaN in modo compatibile

# Importa la funzione di backtesting
from utils.backtesting_engine import run_backtest

# Importa il dizionario delle strategie disponibili dal file di configurazione centralizzato
from utils.strategies_config import STRATEGIE_DISPONIBILI

# Definisci un valore NaN compatibile sia con pandas che numpy
MISSING_VALUE = float('nan')

def run_optimization(
    dati: pd.DataFrame, # DataFrame con dati OHLCV (senza indicatori/segnali iniziali)
    strategia_nome: str, # Nome della strategia da ottimizzare (deve essere in STRATEGIE_DISPONIBILI).
    # Dizionario che definisce i parametri della strategia da ottimizzare e i loro range/step.
    # La struttura è generica e si adatta a qualsiasi numero di parametri.
    # Esempio: {'parametro_A': {'min': v1, 'max': v2, 'step': v3}, 'parametro_B': {'min': w1, 'max': w2, 'step': w3}, ...}
    parametri_ottimizzazione_config: dict,
    capitale_iniziale: float,
    commissione_percentuale: float,
    abilita_short: bool,
    stop_loss_percent: float = None,
    take_profit_percent: float = None,
    trailing_stop_percent: float = None,
    # Puoi aggiungere qui il parametro per la metrica di ottimizzazione (es. 'Rendimento della strategia (%)')
    metrica_ottimizzazione: str = 'Rendimento della strategia (%)',
    # Importo fisso per trade
    investimento_fisso_per_trade: float = None,
    # Parametro per limitare il numero di combinazioni da testare
    max_combinazioni: int = None,
    # Parametro per abilitare l'ottimizzazione parallela
    use_parallel: bool = False,
    # Numero di processi da utilizzare per l'ottimizzazione parallela
    n_jobs: int = -1,
    # Callback per aggiornare il progresso
    progress_callback = None,
    # Numero totale di combinazioni (per il calcolo del progresso)
    total_combinations = None
) -> tuple:
    """
    Esegue l'ottimizzazione dei parametri per una data strategia utilizzando il backtesting.
    Implementa una Grid Search sui parametri specificati.

    Args:
        dati (pd.DataFrame): DataFrame con dati storici (OHLCV).
        strategia_nome (str): Nome della strategia da ottimizzare (deve essere in STRATEGIE_DISPONIBILI).
        parametri_ottimizzazione_config (dict): Dizionario che definisce i parametri della strategia
            da ottimizzare e i loro range/step. Formato:
            {'parametro_nome': {'min': value, 'max': value, 'step': value}, ...}
            Questi parametri devono corrispondere ai nomi dei parametri attesi dalla funzione
            generate_signals della strategia selezionata.
        capitale_iniziale (float): Capitale iniziale per il backtest.
        commissione_percentuale (float): Percentuale di commissione per operazione.
        abilita_short (bool): Se true, le posizioni Short sono permesse.
        stop_loss_percent (float, optional): Percentuale di Stop Loss (fissa durante l'ottimizzazione).
        take_profit_percent (float, optional): Percentuale di Take Profit (fissa durante l'ottimizzazione).
        trailing_stop_percent (float, optional): Percentuale di Trailing Stop (fissa durante l'ottimizzazione).
        metrica_ottimizzazione (str): Il nome della metrica di performance dal backtest_results
            da massimizzare (default: 'Rendimento della strategia (%)').
        investimento_fisso_per_trade (float, optional): Importo fisso da investire per ogni trade.
        max_combinazioni (int, optional): Numero massimo di combinazioni da testare. Se None, testa tutte le combinazioni.
        use_parallel (bool, optional): Se True, esegue l'ottimizzazione in parallelo utilizzando joblib.
        n_jobs (int, optional): Numero di processi da utilizzare per l'ottimizzazione parallela.
            Se -1, utilizza tutti i core disponibili.

    Returns:
        tuple: Una tupla contenente:
            - best_params (dict): Dizionario con i parametri che hanno dato il miglior risultato.
            - best_results (dict): Dizionario con le metriche complete del backtest per i migliori parametri.
            - all_results (list): Lista di dizionari, uno per ogni combinazione testata,
              contenente i parametri e il valore della metrica di ottimizzazione.
            - best_equity_curve (pd.Series): Serie pandas con l'equity curve del miglior backtest.
            - best_buy_hold_equity (pd.Series): Serie pandas con l'equity curve Buy & Hold del miglior backtest.
            - best_trades (list): Lista dei trade eseguiti nel miglior backtest.
            Ritorna ({}, {}, [], pd.Series(), pd.Series(), []) se l'ottimizzazione fallisce o non ci sono combinazioni valide.
    """

    print(f"Inizio ottimizzazione per la strategia: {strategia_nome}")
    print(f"Parametri da ottimizzare: {parametri_ottimizzazione_config}")
    print(f"Metrica di ottimizzazione: {metrica_ottimizzazione}")
    print(f"Nota: I parametri SL, TP e TS sono fissi e non vengono ottimizzati")

    # --- Carica il modulo della strategia dinamicamente ---
    if strategia_nome not in STRATEGIE_DISPONIBILI:
        print(f"Errore ottimizzazione: Strategia '{strategia_nome}' non trovata in STRATEGIE_DISPONIBILI.")
        return {}, {}, [], pd.Series(dtype=float), pd.Series(dtype=float), []

    try:
        # Ottieni il percorso del modulo dalla configurazione
        modulo_path = f"utils.logica_strategie.{STRATEGIE_DISPONIBILI[strategia_nome]['module']}"
        modulo_strategia = importlib.import_module(modulo_path)
        
        # Ottieni il nome della classe dalla configurazione
        class_name = STRATEGIE_DISPONIBILI[strategia_nome]['class']
        
        # Ottieni la classe dal modulo
        strategy_class = getattr(modulo_strategia, class_name)

    except ImportError as e:
        print(f"Errore ottimizzazione: Impossibile importare il modulo strategia '{modulo_path}'. Dettagli: {e}")
        return {}, {}, [], pd.Series(dtype=float), pd.Series(dtype=float), []
    except Exception as e:
        print(f"Errore ottimizzazione: Errore generico durante l'import o la verifica del modulo strategia. Dettagli: {e}")
        return {}, {}, [], pd.Series(dtype=float), pd.Series(dtype=float), []

    # --- Prepara le combinazioni di parametri per la Grid Search ---
    param_names = []
    param_values = []

    for param_name, param_config in parametri_ottimizzazione_config.items():
        if 'min' in param_config and 'max' in param_config and 'step' in param_config:
            param_names.append(param_name)
            values = np.arange(param_config['min'], param_config['max'] + param_config['step'], param_config['step'])
            param_values.append(values.tolist())
        else:
            print(f"Avviso ottimizzazione: Configurazione incompleta per il parametro '{param_name}'. Richiede 'min', 'max', 'step'. Parametro ignorato.")

    if not param_names:
        print("Avviso ottimizzazione: Nessun parametro valido configurato per l'ottimizzazione.")
        return {}, {}, [], pd.Series(dtype=float), pd.Series(dtype=float), []

    param_combinations = list(itertools.product(*param_values))

    # Stima del tempo di elaborazione (assumendo circa 0.5 secondi per combinazione)
    tempo_stimato_sec = len(param_combinations) * 0.5
    tempo_stimato_min = tempo_stimato_sec / 60
    
    if tempo_stimato_min < 1:
        stima_tempo = f"{tempo_stimato_sec:.1f} secondi"
    elif tempo_stimato_min < 60:
        stima_tempo = f"{tempo_stimato_min:.1f} minuti"
    else:
        stima_tempo = f"{tempo_stimato_min/60:.1f} ore"
    
    print(f"Numero totale di combinazioni da testare: {len(param_combinations)} (tempo stimato: {stima_tempo})")
    if len(param_combinations) > 5000:
         print(f"Avviso ottimizzazione: Elevato numero di combinazioni ({len(param_combinations)}). L'ottimizzazione potrebbe richiedere molto tempo. Considera di ridurre i range o aumentare gli step.")

    # --- Esegui Backtest per ogni combinazione ---
    best_performance = -float('inf')
    best_params = {}
    best_results = {}
    best_equity_curve = pd.Series(dtype=float)
    best_buy_hold_equity = pd.Series(dtype=float)
    best_trades = []
    all_results = []

    start_time = time.time()
    processed_count = 0
    
    # Limita il numero di combinazioni se specificato
    if max_combinazioni is not None and max_combinazioni > 0 and max_combinazioni < len(param_combinations):
        print(f"Limitazione a {max_combinazioni} combinazioni su {len(param_combinations)} totali")
        param_combinations = param_combinations[:max_combinazioni]
        
    # Implementazione dell'ottimizzazione parallela se richiesta
    if use_parallel and len(param_combinations) > 1:
        try:
            from joblib import Parallel, delayed
            import multiprocessing
            
            # Determina il numero di processi da utilizzare
            if n_jobs == -1:
                n_jobs = multiprocessing.cpu_count()
            
            print(f"Esecuzione ottimizzazione in parallelo con {n_jobs} processi")
            
            # Funzione per eseguire un singolo backtest in parallelo
            def run_single_backtest(combo, param_names):
                current_params = dict(zip(param_names, combo))
                current_combination_results = current_params.copy()
                
                try:
                    # Crea un'istanza della strategia con i parametri correnti
                    strategy_instance = strategy_class(df=dati.copy(), **current_params)
                    dati_con_segnali = strategy_instance.generate_signals()
                    
                    if dati_con_segnali is None or dati_con_segnali.empty or 'Signal' not in dati_con_segnali.columns:
                        current_combination_results[metrica_ottimizzazione] = MISSING_VALUE
                        return current_combination_results, None, None, None, None, None
                        
                    trades, equity_curve, buy_hold_equity, metriche_risultati = run_backtest(
                        dati_con_segnali,
                        capitale_iniziale=capitale_iniziale,
                        commissione_percentuale=commissione_percentuale,
                        abilita_short=abilita_short,
                        investimento_fisso_per_trade=investimento_fisso_per_trade,
                        stop_loss_percent=stop_loss_percent,
                        take_profit_percent=take_profit_percent,
                        trailing_stop_percent=trailing_stop_percent
                    )
                    
                    # Stampa tutte le metriche disponibili per debug
                    print(f"Metriche disponibili: {list(metriche_risultati.keys())}")
                    
                    # Copia tutte le metriche nei risultati
                    for key, value in metriche_risultati.items():
                        if isinstance(value, (int, float)) or hasattr(value, 'item'):
                            try:
                                # Converti valori numpy in Python standard
                                if hasattr(value, 'item'):
                                    current_combination_results[key] = value.item()
                                else:
                                    current_combination_results[key] = float(value)
                            except (ValueError, TypeError) as e:
                                print(f"Errore nella conversione della metrica {key}: {e}")
                    
                    if metrica_ottimizzazione in metriche_risultati:
                        current_performance = metriche_risultati[metrica_ottimizzazione]
                        # Verifica che il valore non sia NaN prima di assegnarlo
                        if not pd.isna(current_performance) and not math.isnan(current_performance):
                            current_combination_results[metrica_ottimizzazione] = current_performance
                            return current_combination_results, current_params, metriche_risultati, equity_curve, buy_hold_equity, trades
                        else:
                            current_combination_results[metrica_ottimizzazione] = -float('inf')  # Usa un valore molto negativo invece di 0.0
                            return current_combination_results, None, None, None, None, None
                    else:
                        # Se la metrica non esiste, prova a usare una metrica alternativa
                        alternative_metrics = [
                            'Profitto/Perdita Totale (%)', 
                            'Rendimento della strategia (%)',
                            'Capitale Finale (€)',
                            'Profitto/Perdita Totale (€)'
                        ]
                        
                        for alt_metric in alternative_metrics:
                            if alt_metric in metriche_risultati:
                                current_performance = metriche_risultati[alt_metric]
                                if not pd.isna(current_performance) and not math.isnan(current_performance):
                                    current_combination_results[metrica_ottimizzazione] = current_performance
                                    print(f"Usando metrica alternativa '{alt_metric}' invece di '{metrica_ottimizzazione}'")
                                    return current_combination_results, current_params, metriche_risultati, equity_curve, buy_hold_equity, trades
                                break
                        
                        current_combination_results[metrica_ottimizzazione] = -float('inf')  # Usa un valore molto negativo invece di 0.0
                        return current_combination_results, None, None, None, None, None
                        
                except Exception as e:
                    print(f"Errore durante il backtest per parametri {current_params}: {e}")
                    current_combination_results[metrica_ottimizzazione] = 0.0  # Usa 0.0 invece di NaN
                    return current_combination_results, None, None, None, None, None
            
            # Esegui i backtest in parallelo
            results = Parallel(n_jobs=n_jobs)(
                delayed(run_single_backtest)(combo, param_names) for combo in param_combinations
            )
            
            # Elabora i risultati
            for result, params, metrics, equity, bh_equity, trades in results:
                all_results.append(result)
                
                if params is not None and metrics is not None:
                    current_performance = result[metrica_ottimizzazione]
                    # Verifica che il valore non sia NaN prima di confrontarlo
                    if not pd.isna(current_performance) and not math.isnan(current_performance) and current_performance > best_performance:
                        best_performance = current_performance
                        best_params = params.copy()
                        best_results = metrics.copy()
                        best_equity_curve = equity.copy() if equity is not None else pd.Series(dtype=float)
                        best_buy_hold_equity = bh_equity.copy() if bh_equity is not None else pd.Series(dtype=float)
                        best_trades = trades.copy() if trades is not None else []
            
            processed_count = len(param_combinations)
            print(f"Completati {processed_count} backtest in parallelo")
            
        except ImportError:
            print("Modulo joblib non disponibile. Esecuzione in modalità sequenziale.")
            # Continua con l'esecuzione sequenziale se joblib non è disponibile
            for combo in param_combinations:
                current_params = dict(zip(param_names, combo))
                current_combination_results = current_params.copy()

                try:
                    # Crea un'istanza della strategia con i parametri correnti
                    strategy_instance = strategy_class(df=dati.copy(), **current_params)
                    dati_con_segnali = strategy_instance.generate_signals()

                    if dati_con_segnali is None or dati_con_segnali.empty or 'Signal' not in dati_con_segnali.columns:
                         print(f"Avviso ottimizzazione: Generazione segnali fallita o dati non validi per parametri {current_params}. Combinazione saltata.")
                         current_combination_results[metrica_ottimizzazione] = 0.0  # Usa 0.0 invece di NaN
                         all_results.append(current_combination_results)
                         processed_count += 1
                         continue

                except Exception as e:
                    print(f"Errore durante la generazione segnali per parametri {current_params}: {e}. Combinazione saltata.")
                    current_combination_results[metrica_ottimizzazione] = 0.0  # Usa 0.0 invece di NaN
                    all_results.append(current_combination_results)
                    processed_count += 1
                    continue

                try:
                    trades, equity_curve, buy_hold_equity, metriche_risultati = run_backtest(
                        dati_con_segnali,
                        capitale_iniziale=capitale_iniziale,
                        commissione_percentuale=commissione_percentuale,
                        abilita_short=abilita_short,
                        investimento_fisso_per_trade=investimento_fisso_per_trade,
                        stop_loss_percent=stop_loss_percent,
                        take_profit_percent=take_profit_percent,
                        trailing_stop_percent=trailing_stop_percent
                    )

                    # Stampa tutte le metriche disponibili per debug
                    print(f"Metriche disponibili: {list(metriche_risultati.keys())}")
                    
                    # Copia tutte le metriche nei risultati
                    for key, value in metriche_risultati.items():
                        if isinstance(value, (int, float)) or hasattr(value, 'item'):
                            try:
                                # Converti valori numpy in Python standard
                                if hasattr(value, 'item'):
                                    current_combination_results[key] = value.item()
                                else:
                                    current_combination_results[key] = float(value)
                            except (ValueError, TypeError) as e:
                                print(f"Errore nella conversione della metrica {key}: {e}")

                    # Verifica la metrica principale di ottimizzazione
                    if metrica_ottimizzazione in metriche_risultati:
                        current_performance = metriche_risultati[metrica_ottimizzazione]
                        print(f"Valore della metrica '{metrica_ottimizzazione}': {current_performance}")
                        
                        # Verifica che il valore non sia NaN prima di assegnarlo
                        if not pd.isna(current_performance) and not math.isnan(current_performance):
                            current_combination_results[metrica_ottimizzazione] = current_performance
                            if current_performance > best_performance:
                                best_performance = current_performance
                                best_params = current_params.copy()
                                best_results = metriche_risultati.copy()
                                best_equity_curve = equity_curve.copy() if equity_curve is not None else pd.Series(dtype=float)
                                best_buy_hold_equity = buy_hold_equity.copy() if buy_hold_equity is not None else pd.Series(dtype=float)
                                best_trades = trades.copy() if trades is not None else []
                                print(f"Nuovo miglior risultato: {best_performance:.2f} con parametri {best_params}")
                        else:
                            current_combination_results[metrica_ottimizzazione] = 0.0  # Usa 0.0 invece di NaN
                    else:
                        # Se la metrica non esiste, prova a usare una metrica alternativa
                        alternative_metrics = [
                            'Profitto/Perdita Totale (%)', 
                            'Rendimento della strategia (%)',
                            'Capitale Finale (€)',
                            'Profitto/Perdita Totale (€)'
                        ]
                        
                        for alt_metric in alternative_metrics:
                            if alt_metric in metriche_risultati:
                                current_performance = metriche_risultati[alt_metric]
                                if not pd.isna(current_performance) and not math.isnan(current_performance):
                                    current_combination_results[metrica_ottimizzazione] = current_performance
                                    print(f"Usando metrica alternativa '{alt_metric}' invece di '{metrica_ottimizzazione}'")
                                    
                                    # Aggiorna i migliori parametri se la performance è migliore
                                    if current_performance > best_performance:
                                        best_performance = current_performance
                                        best_params = current_params.copy()
                                        best_results = metriche_risultati.copy()
                                        best_equity_curve = equity_curve.copy() if equity_curve is not None else pd.Series(dtype=float)
                                        best_buy_hold_equity = buy_hold_equity.copy() if buy_hold_equity is not None else pd.Series(dtype=float)
                                        best_trades = trades.copy() if trades is not None else []
                                        print(f"Nuovo miglior risultato: {best_performance:.2f} con parametri {best_params}")
                                    break
                        else:
                            print(f"Avviso ottimizzazione: Metrica '{metrica_ottimizzazione}' non trovata nei risultati del backtest per parametri {current_params}.")
                            print(f"Metriche disponibili: {list(metriche_risultati.keys())}")
                            current_combination_results[metrica_ottimizzazione] = -float('inf')  # Usa un valore molto negativo invece di 0.0

                    all_results.append(current_combination_results)

                except Exception as e:
                    print(f"Errore durante il backtest per parametri {current_params}: {e}. Combinazione saltata.")
                    current_combination_results[metrica_ottimizzazione] = -float('inf')  # Usa un valore molto negativo invece di 0.0
                    all_results.append(current_combination_results)

                processed_count += 1
                if processed_count % 10 == 0 or processed_count == len(param_combinations):
                     elapsed_time = time.time() - start_time
                     print(f"Processate {processed_count}/{len(param_combinations)} combinazioni. Tempo trascorso: {elapsed_time:.2f}s")
    else:
        # Esecuzione sequenziale standard
        for combo in param_combinations:
            current_params = dict(zip(param_names, combo))
            current_combination_results = current_params.copy()

            try:
                # Crea un'istanza della strategia con i parametri correnti
                # Assicurati che i dati abbiano le colonne nel formato corretto per la strategia
                dati_per_strategia = dati.copy()
                
                # Standardizza i nomi delle colonne per la strategia (maiuscole)
                if isinstance(dati_per_strategia.columns, pd.MultiIndex):
                    dati_per_strategia.columns = dati_per_strategia.columns.get_level_values(0)
                
                # Verifica che le colonne necessarie esistano prima di convertirle in maiuscolo
                required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                missing_cols = [col for col in required_cols if col not in dati_per_strategia.columns]
                if missing_cols:
                    print(f"Errore: DataFrame mancante di colonne OHLCV essenziali. Mancanti: {missing_cols}")
                    print(f"Colonne disponibili: {dati_per_strategia.columns.tolist()}")
                    return {}, {}, [], pd.Series(dtype=float), pd.Series(dtype=float), []
                
                # Converti i nomi delle colonne in maiuscolo
                dati_per_strategia.columns = [col.upper() for col in dati_per_strategia.columns]
                
                strategy_instance = strategy_class(df=dati_per_strategia, **current_params)
                dati_con_segnali = strategy_instance.generate_signals()

                if dati_con_segnali is None or dati_con_segnali.empty or 'Signal' not in dati_con_segnali.columns:
                     print(f"Avviso ottimizzazione: Generazione segnali fallita o dati non validi per parametri {current_params}. Combinazione saltata.")
                     current_combination_results[metrica_ottimizzazione] = -float('inf')  # Usa un valore molto negativo invece di 0.0
                     all_results.append(current_combination_results)
                     processed_count += 1
                     continue

            except Exception as e:
                print(f"Errore durante la generazione segnali per parametri {current_params}: {e}. Combinazione saltata.")
                current_combination_results[metrica_ottimizzazione] = -float('inf')  # Usa un valore molto negativo invece di 0.0
                all_results.append(current_combination_results)
                processed_count += 1
                continue

            try:
                # Assicurati che i dati abbiano le colonne nel formato corretto per il backtest (prima lettera maiuscola)
                dati_per_backtest = dati_con_segnali.copy()
                
                # Rinomina le colonne nel formato richiesto dal backtest
                column_mapping = {
                    'OPEN': 'Open', 
                    'HIGH': 'High', 
                    'LOW': 'Low', 
                    'CLOSE': 'Close', 
                    'VOLUME': 'Volume'
                }
                
                # Verifica che le colonne necessarie esistano prima di rinominarle
                missing_cols = [old_col for old_col in ['OPEN', 'HIGH', 'LOW', 'CLOSE'] if old_col not in dati_per_backtest.columns]
                if missing_cols:
                    print(f"Errore: DataFrame mancante di colonne OHLC essenziali. Mancanti: {missing_cols}")
                    print(f"Colonne disponibili: {dati_per_backtest.columns.tolist()}")
                    current_combination_results[metrica_ottimizzazione] = -float('inf')
                    all_results.append(current_combination_results)
                    processed_count += 1
                    continue
                
                for old_col, new_col in column_mapping.items():
                    if old_col in dati_per_backtest.columns:
                        dati_per_backtest.rename(columns={old_col: new_col}, inplace=True)
                
                trades, equity_curve, buy_hold_equity, metriche_risultati = run_backtest(
                    dati_per_backtest,
                    capitale_iniziale=capitale_iniziale,
                    commissione_percentuale=commissione_percentuale,
                    abilita_short=abilita_short,
                    investimento_fisso_per_trade=investimento_fisso_per_trade,
                    stop_loss_percent=stop_loss_percent,
                    take_profit_percent=take_profit_percent,
                    trailing_stop_percent=trailing_stop_percent
                )

                # Stampa tutte le metriche disponibili per debug
                print(f"Metriche disponibili: {list(metriche_risultati.keys())}")
                
                # Copia tutte le metriche nei risultati
                for key, value in metriche_risultati.items():
                    if isinstance(value, (int, float)) or hasattr(value, 'item'):
                        try:
                            # Converti valori numpy in Python standard
                            if hasattr(value, 'item'):
                                current_combination_results[key] = value.item()
                            else:
                                current_combination_results[key] = float(value)
                        except (ValueError, TypeError) as e:
                            print(f"Errore nella conversione della metrica {key}: {e}")

                # Verifica la metrica principale di ottimizzazione
                if metrica_ottimizzazione in metriche_risultati:
                    current_performance = metriche_risultati[metrica_ottimizzazione]
                    print(f"Valore della metrica '{metrica_ottimizzazione}': {current_performance}")
                    
                    # Verifica che il valore non sia NaN prima di assegnarlo
                    if not pd.isna(current_performance) and not math.isnan(current_performance):
                        current_combination_results[metrica_ottimizzazione] = current_performance
                        if current_performance > best_performance:
                            best_performance = current_performance
                            best_params = current_params.copy()
                            best_results = metriche_risultati.copy()
                            best_equity_curve = equity_curve.copy() if equity_curve is not None else pd.Series(dtype=float)
                            best_buy_hold_equity = buy_hold_equity.copy() if buy_hold_equity is not None else pd.Series(dtype=float)
                            best_trades = trades.copy() if trades is not None else []
                            print(f"Nuovo miglior risultato: {best_performance:.2f} con parametri {best_params}")
                    else:
                        current_combination_results[metrica_ottimizzazione] = 0.0  # Usa 0.0 invece di NaN
                else:
                    # Se la metrica non esiste, prova a usare una metrica alternativa
                    alternative_metrics = [
                        'Profitto/Perdita Totale (%)', 
                        'Rendimento della strategia (%)',
                        'Capitale Finale (€)',
                        'Profitto/Perdita Totale (€)'
                    ]
                    
                    for alt_metric in alternative_metrics:
                        if alt_metric in metriche_risultati:
                            current_performance = metriche_risultati[alt_metric]
                            if not pd.isna(current_performance) and not math.isnan(current_performance):
                                current_combination_results[metrica_ottimizzazione] = current_performance
                                print(f"Usando metrica alternativa '{alt_metric}' invece di '{metrica_ottimizzazione}'")
                                
                                # Aggiorna i migliori parametri se la performance è migliore
                                if current_performance > best_performance:
                                    best_performance = current_performance
                                    best_params = current_params.copy()
                                    best_results = metriche_risultati.copy()
                                    best_equity_curve = equity_curve.copy() if equity_curve is not None else pd.Series(dtype=float)
                                    best_buy_hold_equity = buy_hold_equity.copy() if buy_hold_equity is not None else pd.Series(dtype=float)
                                    best_trades = trades.copy() if trades is not None else []
                                    print(f"Nuovo miglior risultato: {best_performance:.2f} con parametri {best_params}")
                                break
                    else:
                        print(f"Avviso ottimizzazione: Metrica '{metrica_ottimizzazione}' non trovata nei risultati del backtest per parametri {current_params}.")
                        print(f"Metriche disponibili: {list(metriche_risultati.keys())}")
                        current_combination_results[metrica_ottimizzazione] = 0.0  # Usa 0.0 invece di NaN

                all_results.append(current_combination_results)

            except Exception as e:
                print(f"Errore durante il backtest per parametri {current_params}: {e}. Combinazione saltata.")
                current_combination_results[metrica_ottimizzazione] = 0.0  # Usa 0.0 invece di NaN
                all_results.append(current_combination_results)

            processed_count += 1
            if processed_count % 10 == 0 or processed_count == len(param_combinations):
                 elapsed_time = time.time() - start_time
                 print(f"Processate {processed_count}/{len(param_combinations)} combinazioni. Tempo trascorso: {elapsed_time:.2f}s")
                 # Aggiorna il progresso tramite callback se disponibile
                 if progress_callback and total_combinations:
                     progress_callback(processed_count, total_combinations)

    end_time = time.time()
    total_time = end_time - start_time
    print(f"Ottimizzazione completata in {total_time:.2f} secondi.")
    
    # Verifica che best_performance non sia NaN prima di stamparlo
    if not math.isnan(best_performance):
        print(f"Miglior valore della metrica '{metrica_ottimizzazione}': {best_performance:.2f}")
    else:
        print(f"Miglior valore della metrica '{metrica_ottimizzazione}': Non disponibile (NaN)")
        
    # Stampa i migliori parametri dopo le metriche di performance
    print(f"Migliori parametri trovati: {best_params}")

    # Assicurati che tutti i risultati siano serializzabili
    for result in all_results:
        for key in list(result.keys()):
            if hasattr(result[key], 'item'):
                try:
                    result[key] = result[key].item()
                except:
                    result[key] = float(result[key])

    return best_params, best_results, all_results, best_equity_curve, best_buy_hold_equity, best_trades

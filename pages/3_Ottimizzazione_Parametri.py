# ottimizzazione parametri
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
import os
import json
import importlib
import plotly.graph_objects as go
import plotly.express as px
import time

# Importazioni dai moduli di utilità
from utils.importazione_dati import load_tickers_from_csv, download_stock_data, get_ticker_list_for_selection, extract_symbol_from_selection
from utils.strategies_config import STRATEGIE_DISPONIBILI
from utils.ottimizzazione_engine import run_optimization
from utils.backtesting_engine import run_backtest
from utils.plotting_utils import plot_backtest_results, plot_equity_curves as plot_equity_comparison

# --- Configurazione della pagina Streamlit ---
st.set_page_config(
    page_title="Ottimizzazione Parametri",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Ottimizzazione Parametri Strategia")
st.markdown("Trova i parametri ottimali per le tue strategie di trading su dati storici.")

# --- Inizializzazione dello stato della sessione ---
if 'optimization_running' not in st.session_state:
    st.session_state.optimization_running = False
if 'optimization_done' not in st.session_state:
    st.session_state.optimization_done = False
if 'data_scaricati' not in st.session_state:
    st.session_state.data_scaricati = pd.DataFrame()
if 'data_scaricati_ticker' not in st.session_state:
    st.session_state.data_scaricati_ticker = None
if 'data_scaricati_start_date' not in st.session_state:
    st.session_state.data_scaricati_start_date = None
if 'data_scaricati_end_date' not in st.session_state:
    st.session_state.data_scaricati_end_date = None
if 'selected_ticker_symbol_opt' not in st.session_state:
    st.session_state.selected_ticker_symbol_opt = None
if 'best_params' not in st.session_state:
    st.session_state.best_params = {}
if 'best_metrics' not in st.session_state:
    st.session_state.best_metrics = {}
if 'all_optimization_results' not in st.session_state:
    st.session_state.all_optimization_results = []
if 'best_equity_curve' not in st.session_state:
    st.session_state.best_equity_curve = pd.Series(dtype=float)
if 'best_buy_hold_equity' not in st.session_state:
    st.session_state.best_buy_hold_equity = pd.Series(dtype=float)
if 'best_trades' not in st.session_state:
    st.session_state.best_trades = []

def reset_optimization_state():
    """Resetta lo stato dell'ottimizzazione"""
    st.session_state.best_params = {}
    st.session_state.best_metrics = {}
    st.session_state.all_optimization_results = []
    st.session_state.best_equity_curve = pd.Series(dtype=float)
    st.session_state.best_buy_hold_equity = pd.Series(dtype=float)
    st.session_state.best_trades = []
    # Non resettare i dati scaricati
    # st.session_state.data_scaricati = pd.DataFrame()

# --- UI per Selezione Dati ---
st.subheader("1. Seleziona Dati per Ottimizzazione")

col1, col2 = st.columns([2, 1])

with col1:
    # Carica i ticker disponibili
    tickers_file_path = "tickers.csv"
    tickers_for_selection = get_ticker_list_for_selection(tickers_file_path)
    
    if not tickers_for_selection:
        st.error("Impossibile caricare la lista dei ticker. Verifica che il file 'tickers.csv' esista nella cartella principale del progetto e sia formattato correttamente.")
    else:
        selected_ticker_display = st.selectbox(
            "Seleziona un Titolo Azionario:",
            options=tickers_for_selection
        )
        ticker_symbol = extract_symbol_from_selection(selected_ticker_display)
        st.session_state.selected_ticker_symbol_opt = ticker_symbol

with col2:
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date = st.date_input("Data Inizio:", date(2022, 1, 1))
    with col_date2:
        end_date = st.date_input("Data Fine:", date.today())

# --- UI per Configurazione Strategia ---
st.subheader("2. Configura Strategia e Parametri da Ottimizzare")

# Selezione della strategia
selected_strategy_name = st.selectbox(
    "Scegli la Strategia da Ottimizzare:",
    options=list(STRATEGIE_DISPONIBILI.keys())
)

# Mostra descrizione della strategia
if selected_strategy_name in STRATEGIE_DISPONIBILI:
    strategy_info = STRATEGIE_DISPONIBILI[selected_strategy_name]
    st.info(f"**Descrizione:** {strategy_info['description']}")

# Configurazione dei parametri da ottimizzare
st.write("### Parametri da Ottimizzare")
st.write("Definisci il range di valori per ogni parametro da ottimizzare:")

optimization_config = {}

if selected_strategy_name in STRATEGIE_DISPONIBILI:
    strategy_info = STRATEGIE_DISPONIBILI[selected_strategy_name]
    
    for param_name, param_details in strategy_info['parameters'].items():
        param_type = param_details['type']
        param_default = param_details['default']
        param_min = param_details['min_value']
        param_max = param_details['max_value']
        param_step = param_details['step']
        param_label = param_details['label']
        param_help = f"Parametro: {param_label} (default: {param_default})"
        
        st.write(f"**{param_name}**")
        
        key_min = f"{param_name}_min_opt"
        key_max = f"{param_name}_max_opt"
        key_step = f"{param_name}_step_opt"

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            p_min = st.number_input("Min", value=param_min, step=param_step, key=key_min, help=param_help)
        with col_p2:
            p_max = st.number_input("Max", value=param_max, step=param_step, key=key_max, help=param_help)
        with col_p3:
            p_step = st.number_input("Step", value=param_step, step=0.01 if param_type == 'float' else 1, key=key_step, help="Incremento per l'ottimizzazione")

        if p_min > p_max:
            st.error(f"Errore: Il valore minimo per '{param_name}' ({p_min}) non può essere maggiore del massimo ({p_max}).")
            optimization_config = {}
            break
        
        optimization_config[param_name] = {
            'min': p_min,
            'max': p_max,
            'step': p_step,
            'type': param_type
        }

# Parametri di backtest fissi
st.write("### Parametri di Backtest Fissi")

col_cap1, col_cap2 = st.columns(2)
with col_cap1:
    capitale_iniziale = st.number_input("Capitale Iniziale (€):", min_value=100.0, value=10000.0, step=100.0)
with col_cap2:
    investimento_fisso_per_trade = st.number_input(
        "Importo Fisso per Trade (€):",
        min_value=0.0,
        value=5000.0,
        step=100.0,
        help="Importo fisso da investire per ogni trade. Imposta a 0 per usare una percentuale del capitale disponibile."
    )

col_comm1, col_comm2 = st.columns(2)
with col_comm1:
    commissione_percentuale = st.number_input("Commissione (%):", min_value=0.0, max_value=5.0, value=0.2, step=0.01, format="%.2f")
with col_comm2:
    abilita_short = st.checkbox("Abilita Posizioni SHORT", value=True)

st.write("Parametri di Gestione del Rischio:")
col_risk1, col_risk2, col_risk3 = st.columns(3)
with col_risk1:
    stop_loss_percent = st.number_input("Stop Loss (%):", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.1f")
    if stop_loss_percent == 0.0: stop_loss_percent = None
with col_risk2:
    take_profit_percent = st.number_input("Take Profit (%):", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.1f")
    if take_profit_percent == 0.0: take_profit_percent = None
with col_risk3:
    trailing_stop_percent = st.number_input("Trailing Stop (%):", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.1f")
    if trailing_stop_percent == 0.0: trailing_stop_percent = None

# --- UI per Esecuzione Ottimizzazione ---
st.subheader("3. Esegui Ottimizzazione")

# Calcola il numero di combinazioni da testare
num_combinations = 1
for param_name, param_config in optimization_config.items():
    if 'min' in param_config and 'max' in param_config and 'step' in param_config:
        min_val = param_config['min']
        max_val = param_config['max']
        step_val = param_config['step']
        num_values = int((max_val - min_val) / step_val) + 1
        num_combinations *= num_values

# Stima del tempo di elaborazione (assumendo circa 1 secondo per combinazione)
tempo_stimato_sec = num_combinations * 1.0
tempo_stimato_min = tempo_stimato_sec / 60

if tempo_stimato_min < 1:
    stima_tempo = f"{tempo_stimato_sec:.1f} secondi"
elif tempo_stimato_min < 60:
    stima_tempo = f"{tempo_stimato_min:.1f} minuti"
else:
    stima_tempo = f"{tempo_stimato_min/60:.1f} ore"

st.info(f"Numero di combinazioni da testare: {num_combinations} (tempo stimato: {stima_tempo})")

# Modifica la condizione per abilitare il pulsante
button_disabled = st.session_state.optimization_running or st.session_state.selected_ticker_symbol_opt is None or not optimization_config

if st.button("Avvia Ottimizzazione", type="primary", disabled=button_disabled):
    # Scarica i dati qui, quando l'utente clicca su "Avvia Ottimizzazione"
    with st.spinner(f"Scaricamento dati per {st.session_state.selected_ticker_symbol_opt}..."):
        dati = download_stock_data(
            st.session_state.selected_ticker_symbol_opt, 
            start_date, 
            end_date
        )
        
        if dati is None or dati.empty:
            st.error("Impossibile scaricare i dati per il ticker selezionato.")
            st.stop()
            
        # Standardizza i nomi delle colonne
        if isinstance(dati.columns, pd.MultiIndex):
            dati.columns = dati.columns.get_level_values(0)
        dati.columns = [col.upper() for col in dati.columns]

# Aggiungi queste righe per rinominare le colonne nel formato corretto per il backtester
        dati_for_backtest = dati.copy()
        
        # Stampa le colonne disponibili per debug
        st.write(f"Colonne disponibili nei dati: {dati_for_backtest.columns.tolist()}")
        
        # Verifica se le colonne sono in formato maiuscolo o minuscolo
        if 'CLOSE' in dati_for_backtest.columns:
            dati_for_backtest.rename(columns={'CLOSE': 'Close'}, inplace=True)
        if 'OPEN' in dati_for_backtest.columns:
            dati_for_backtest.rename(columns={'OPEN': 'Open'}, inplace=True)
        if 'HIGH' in dati_for_backtest.columns:
            dati_for_backtest.rename(columns={'HIGH': 'High'}, inplace=True)
        if 'LOW' in dati_for_backtest.columns:
            dati_for_backtest.rename(columns={'LOW': 'Low'}, inplace=True)
        if 'VOLUME' in dati_for_backtest.columns:
            dati_for_backtest.rename(columns={'VOLUME': 'Volume'}, inplace=True)
            
        # Verifica che le colonne necessarie esistano dopo la rinomina
        required_cols = ['Open', 'High', 'Low', 'Close']
        missing_cols = [col for col in required_cols if col not in dati_for_backtest.columns]
        if missing_cols:
            st.error(f"Errore: Colonne necessarie mancanti dopo la rinomina: {missing_cols}")
            st.error(f"Colonne disponibili: {dati_for_backtest.columns.tolist()}")
            st.stop()

# Usa dati_for_backtest invece di dati.copy() quando chiami run_optimization
        
        # Verifica che i dati contengano le colonne necessarie
        required_cols = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
        if not all(col in dati.columns for col in required_cols):
            st.error(f"I dati scaricati non contengono tutte le colonne necessarie: {required_cols}")
            st.stop()
            
        st.success(f"Dati scaricati: {len(dati)} record")
        
        # Salva i dati nella sessione
        st.session_state.data_scaricati = dati
        st.session_state.data_scaricati_ticker = st.session_state.selected_ticker_symbol_opt
        st.session_state.data_scaricati_start_date = start_date
        st.session_state.data_scaricati_end_date = end_date
    
    # Test della strategia selezionata con i dati appena scaricati
    try:
        # Ottieni il percorso del modulo dalla configurazione
        modulo_path = f"utils.logica_strategie.{STRATEGIE_DISPONIBILI[selected_strategy_name]['module']}"
        class_name = STRATEGIE_DISPONIBILI[selected_strategy_name]['class']
        
        # Importa dinamicamente il modulo e la classe della strategia
        strategy_module = importlib.import_module(modulo_path)
        strategy_class = getattr(strategy_module, class_name)
        
        # Crea un dizionario con i valori predefiniti dei parametri
        default_params = {}
        for param_name, param_config in STRATEGIE_DISPONIBILI[selected_strategy_name]['parameters'].items():
            default_params[param_name] = param_config['default']
        
        # Crea un'istanza della strategia con i parametri predefiniti
        test_strategy = strategy_class(df=dati_for_backtest, **default_params)
        test_df = test_strategy.generate_signals()
        
        st.write(f"Test strategia: {len(test_df)} righe con segnali generati")
        st.write(f"Numero di segnali non zero: {(test_df['Signal'] != 0).sum()}")
    except Exception as e:
        st.error(f"Errore nel test della strategia: {e}")
        st.stop()
    
    # Avvia l'ottimizzazione
    st.session_state.optimization_running = True
    st.session_state.optimization_done = False
    reset_optimization_state()
    
    # Crea un placeholder per mostrare il progresso dell'ottimizzazione
    progress_placeholder = st.empty()
    progress_bar = progress_placeholder.progress(0)
    status_text = st.empty()
    
    # Inizializza il contatore di combinazioni processate
    processed_count = 0
    
    try:
        # Funzione di callback per aggiornare la barra di progresso
        def update_progress(current_count, total_count):
            # Aggiorna la barra di progresso
            progress = min(current_count / total_count, 1.0)
            progress_bar.progress(progress)
            
            # Aggiorna il testo di stato
            elapsed_time = time.time() - start_time
            estimated_total_time = elapsed_time / progress if progress > 0 else 0
            remaining_time = estimated_total_time - elapsed_time
            
            if remaining_time < 60:
                time_text = f"{remaining_time:.1f} secondi"
            elif remaining_time < 3600:
                time_text = f"{remaining_time/60:.1f} minuti"
            else:
                time_text = f"{remaining_time/3600:.1f} ore"
            
            status_text.text(f"Processate {current_count}/{total_count} combinazioni. Tempo rimanente stimato: {time_text}")
        
        # Registra il tempo di inizio
        start_time = time.time()
        
        # Calcola le metriche per ogni combinazione di parametri
        best_params, best_metrics, all_results, *_ = run_optimization(
            dati=dati_for_backtest,  # <-- Usa i dati con le colonne rinominate
            strategia_nome=selected_strategy_name,
            parametri_ottimizzazione_config=optimization_config,
            capitale_iniziale=capitale_iniziale,
            commissione_percentuale=commissione_percentuale,
            abilita_short=abilita_short,
            investimento_fisso_per_trade=investimento_fisso_per_trade if investimento_fisso_per_trade > 0 else None,
            stop_loss_percent=stop_loss_percent,
            take_profit_percent=take_profit_percent,
            trailing_stop_percent=trailing_stop_percent,
            metrica_ottimizzazione="Rendimento della strategia (%)",
            progress_callback=update_progress,
            total_combinations=num_combinations
        )
        
        # Salva i risultati nello stato della sessione
        st.session_state.best_params = best_params
        st.session_state.best_metrics = best_metrics
        st.session_state.all_optimization_results = all_results
        st.session_state.optimization_done = True
            
        # Esegui un backtest con i migliori parametri per ottenere equity curve e trades
        if best_params:
            try:
                # Ottieni il percorso del modulo dalla configurazione
                modulo_path = f"utils.logica_strategie.{STRATEGIE_DISPONIBILI[selected_strategy_name]['module']}"
                modulo_strategia_finale = importlib.import_module(modulo_path)
                
                # Genera i segnali con i migliori parametri
                class_name = STRATEGIE_DISPONIBILI[selected_strategy_name]['class']
                strategy_class = getattr(modulo_strategia_finale, class_name)
                strategy_instance = strategy_class(df=dati_for_backtest, **best_params)
                dati_con_segnali_finali = strategy_instance.generate_signals()
                
                if hasattr(strategy_instance, 'get_indicator_columns'):
                    indicator_cols_finali = strategy_instance.get_indicator_columns()
                else:
                    indicator_cols_finali = []
                
                if dati_con_segnali_finali is not None and not dati_con_segnali_finali.empty and 'Signal' in dati_con_segnali_finali.columns:
                    # Rinomina le colonne OHLC in formato titolo per il backtest
                    dati_finali_backtest = dati_con_segnali_finali.copy()
                    if 'CLOSE' in dati_finali_backtest.columns:
                        dati_finali_backtest.rename(columns={'CLOSE': 'Close'}, inplace=True)
                    if 'OPEN' in dati_finali_backtest.columns:
                        dati_finali_backtest.rename(columns={'OPEN': 'Open'}, inplace=True)
                    if 'HIGH' in dati_finali_backtest.columns:
                        dati_finali_backtest.rename(columns={'HIGH': 'High'}, inplace=True)
                    if 'LOW' in dati_finali_backtest.columns:
                        dati_finali_backtest.rename(columns={'LOW': 'Low'}, inplace=True)
                    if 'VOLUME' in dati_finali_backtest.columns:
                        dati_finali_backtest.rename(columns={'VOLUME': 'Volume'}, inplace=True)
                    
                    # Verifica che le colonne necessarie esistano dopo la rinomina
                    required_cols = ['Open', 'High', 'Low', 'Close']
                    missing_cols = [col for col in required_cols if col not in dati_finali_backtest.columns]
                    if missing_cols:
                        st.error(f"Errore: Colonne necessarie mancanti nei dati finali: {missing_cols}")
                        st.error(f"Colonne disponibili: {dati_finali_backtest.columns.tolist()}")
                    else:
                        best_trades, best_equity, best_bh_equity, best_metrics = run_backtest(
                            dati_finali_backtest,
                            capitale_iniziale=capitale_iniziale,
                            commissione_percentuale=commissione_percentuale,
                            abilita_short=abilita_short,
                            investimento_fisso_per_trade=investimento_fisso_per_trade if investimento_fisso_per_trade > 0 else None,
                            stop_loss_percent=stop_loss_percent,
                            take_profit_percent=take_profit_percent,
                            trailing_stop_percent=trailing_stop_percent
                        )
                        st.session_state.best_trades = best_trades
                        st.session_state.best_equity_curve = best_equity
                        st.session_state.best_buy_hold_equity = best_bh_equity
                        st.session_state.best_metrics = best_metrics  # Aggiorna con le metriche dal backtest finale
                        
                        # Converti le date in stringhe per evitare problemi di visualizzazione
                        for key in st.session_state.best_metrics:
                            if 'Data' in key and st.session_state.best_metrics[key] != 'N/A':
                                st.session_state.best_metrics[key] = str(st.session_state.best_metrics[key])
                                
                        st.success("Backtest finale completato.")
            except Exception as e:
                st.error(f"Errore durante l'esecuzione del backtest finale: {e}")
            
    except Exception as e:
        st.error(f"Errore durante l'ottimizzazione: {e}")
    finally:
        # Completa la barra di progresso e rimuovi il testo di stato
        progress_bar.progress(1.0)
        status_text.empty()
        st.session_state.optimization_running = False

# --- Visualizzazione dei Risultati dell'Ottimizzazione ---
if st.session_state.optimization_done:
    st.header("Risultati dell'Ottimizzazione")
    
    # Mostra i migliori parametri trovati
    if st.session_state.best_params:
        st.subheader("Migliori Parametri Trovati")
        
        # Crea una tabella per i migliori parametri
        best_params_df = pd.DataFrame({
            'Parametro': list(st.session_state.best_params.keys()),
            'Valore Ottimale': list(st.session_state.best_params.values())
        })
        st.dataframe(best_params_df)
        
        # Mostra le metriche di performance
        st.subheader("Metriche di Performance con i Migliori Parametri")
        if st.session_state.best_metrics:
            # Calcola metriche aggiuntive per l'ottimizzazione
            total_commission_opt = sum(trade.get('Comm. (€)', 0) for trade in st.session_state.best_trades) if st.session_state.best_trades else 0
            winning_trades_opt = len([t for t in st.session_state.best_trades if t.get('P/L (€)', 0) > 0]) if st.session_state.best_trades else 0
            losing_trades_opt = len([t for t in st.session_state.best_trades if t.get('P/L (€)', 0) < 0]) if st.session_state.best_trades else 0
            
            # Calcola Profit Factor
            gross_profit_opt = sum(t.get('P/L (€)', 0) for t in st.session_state.best_trades if t.get('P/L (€)', 0) > 0) if st.session_state.best_trades else 0
            gross_loss_opt = abs(sum(t.get('P/L (€)', 0) for t in st.session_state.best_trades if t.get('P/L (€)', 0) < 0)) if st.session_state.best_trades else 0
            profit_factor_opt = gross_profit_opt / gross_loss_opt if gross_loss_opt != 0 else float('inf')
            
            # Calcola Reward/Risk Ratio
            avg_win_opt = gross_profit_opt / winning_trades_opt if winning_trades_opt > 0 else 0
            avg_loss_opt = gross_loss_opt / losing_trades_opt if losing_trades_opt > 0 else 0
            reward_risk_ratio_opt = avg_win_opt / avg_loss_opt if avg_loss_opt != 0 else float('inf')
            
            # Calcola Buy & Hold Return
            buy_hold_return_opt = ((st.session_state.best_buy_hold_equity.iloc[-1] / capitale_iniziale) - 1) * 100 if not st.session_state.best_buy_hold_equity.empty else 0
            
            # Crea il dizionario delle metriche nell'ordine esatto richiesto
            metriche_complete = {
                'Nome del Titolo': selected_ticker_display,
                'Strategia': selected_strategy_name,
                'Data Iniziale del Test': start_date.strftime('%Y-%m-%d'),
                'Data Finale del Test': end_date.strftime('%Y-%m-%d'),
                'Parametri Ottimali': str(st.session_state.best_params),
                'Capitale Iniziale (€)': capitale_iniziale,
                'Commissione (%)': commissione_percentuale,
                'Abilita Short': 'Sì' if abilita_short else 'No',
                'Importo Fisso per Trade (€)': investimento_fisso_per_trade if investimento_fisso_per_trade > 0 else 'N/A',
                'Stop Loss (%)': stop_loss_percent if stop_loss_percent is not None else 'N/A',
                'Take Profit (%)': take_profit_percent if take_profit_percent is not None else 'N/A',
                'Trailing Stop (%)': trailing_stop_percent if trailing_stop_percent is not None else 'N/A',
                'Capitale Finale (€)': st.session_state.best_metrics.get('Capitale Finale (€)', 0),
                'Profitto/Perdita Totale (€)': st.session_state.best_metrics.get('Profitto/Perdita Totale (€)', 0),
                'Profitto/Perdita Totale (%)': st.session_state.best_metrics.get('Profitto/Perdita Totale (%)', 0),
                'Giorni Totali': st.session_state.best_metrics.get('Giorni Totali', 0),
                'Rendimento Medio Annuale (%)': st.session_state.best_metrics.get('Rendimento Medio Annuale (%)', 0),
                'Spese di Commissione Totali (€)': round(total_commission_opt, 2),
                'Numero Totale di Trade': st.session_state.best_metrics.get('Numero Totale di Trade', 0),
                'Num. Trade Vincenti': st.session_state.best_metrics.get('Num. Trade Vincenti', 0),
                'Num. Trade Perdenti': st.session_state.best_metrics.get('Num. Trade Perdenti', 0),
                'Percentuale Trade Vincenti': st.session_state.best_metrics.get('Percentuale Trade Vincenti', 0),
                'Num. Trade Long': st.session_state.best_metrics.get('Num. Trade Long', 0),
                'P/L Medio Trade Long (%)': st.session_state.best_metrics.get('P/L Medio Trade Long (%)', 0),
                'Num. Trade Short': st.session_state.best_metrics.get('Num. Trade Short', 0),
                'P/L Medio Trade Short (%)': st.session_state.best_metrics.get('P/L Medio Trade Short (%)', 0),
                'Profitto Medio Trade Vincenti (€)': st.session_state.best_metrics.get('Profitto Medio Trade Vincenti (€)', 0),
                'Profitto Medio Trade Vincenti (%)': st.session_state.best_metrics.get('Profitto Medio Trade Vincenti (%)', 0),
                'Perdita Media Trade Perdenti (€)': st.session_state.best_metrics.get('Perdita Media Trade Perdenti (€)', 0),
                'Perdita Media Trade Perdenti (%)': st.session_state.best_metrics.get('Perdita Media Trade Perdenti (%)', 0),
                'Profitto Massimo Trade (€)': st.session_state.best_metrics.get('Profitto Massimo Trade (€)', 0),
                'Profitto Massimo Trade (%)': st.session_state.best_metrics.get('Profitto Massimo Trade (%)', 0),
                'Data Profitto Massimo': st.session_state.best_metrics.get('Data Profitto Massimo', 'N/A'),
                'Perdita Massima Trade (€)': st.session_state.best_metrics.get('Perdita Massima Trade (€)', 0),
                'Perdita Massima Trade (%)': st.session_state.best_metrics.get('Perdita Massima Trade (%)', 0),
                'Data Perdita Massima': st.session_state.best_metrics.get('Data Perdita Massima', 'N/A'),
                'Durata Media Trade (giorni)': st.session_state.best_metrics.get('Durata Media Trade (giorni)', 0),
                'Max Drawdown (€)': st.session_state.best_metrics.get('Max Drawdown (€)', 0),
                'Max Drawdown (%)': st.session_state.best_metrics.get('Max Drawdown (%)', 0),
                'Ratio Sharpe': st.session_state.best_metrics.get('Ratio Sharpe', 0),
                'Ratio Sortino': st.session_state.best_metrics.get('Ratio Sortino', 0),
                'Ratio Calmar': st.session_state.best_metrics.get('Ratio Calmar', 0),
                'Profit Factor': round(profit_factor_opt, 2),
                'Reward/Risk Ratio': round(reward_risk_ratio_opt, 2),
                'Buy & Hold Return (%)': round(buy_hold_return_opt, 2)
            }

            
            # Crea un dataframe con le metriche
            metrics_df = pd.DataFrame({
                'Metrica': list(metriche_complete.keys()),
                'Valore': list(metriche_complete.values())
            })
            
            # Visualizza il dataframe
            st.dataframe(metrics_df, use_container_width=True)
        
        # Mostra l'equity curve
        if not st.session_state.best_equity_curve.empty:
            st.subheader("Equity Curve con i Migliori Parametri")
            fig = plot_equity_comparison(
                st.session_state.best_equity_curve,
                st.session_state.best_buy_hold_equity
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Mostra i trade eseguiti
        if st.session_state.best_trades:
            st.subheader("Trade Eseguiti con i Migliori Parametri")
            trades_df = pd.DataFrame(st.session_state.best_trades)
            st.dataframe(trades_df)
    
    # Mostra tutti i risultati dell'ottimizzazione
    if st.session_state.all_optimization_results:
        st.subheader("Tutti i Risultati dell'Ottimizzazione")
        all_results_df = pd.DataFrame(st.session_state.all_optimization_results)
        st.dataframe(all_results_df)
        
        # Visualizza graficamente i risultati dell'ottimizzazione
        param_names = list(optimization_config.keys())
        if len(param_names) == 1:
            # Grafico per un solo parametro
            param_name = param_names[0]
            st.subheader(f"Grafico di Ottimizzazione per {param_name}")
            
            fig = px.line(
                all_results_df.sort_values(by=param_name),
                x=param_name,
                y="Rendimento della strategia (%)",
                title=f"Rendimento vs {param_name}",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
            
        elif len(param_names) == 2:
            # Grafico per due parametri
            st.subheader(f"Grafico di Ottimizzazione per {param_names[0]} e {param_names[1]}")
            
            # Opzioni di visualizzazione
            viz_options = ["Scatter 3D", "Surface 3D", "Heatmap"]
            selected_viz = st.selectbox("Seleziona tipo di visualizzazione:", viz_options)
            
            if selected_viz == "Scatter 3D":
                fig = px.scatter_3d(
                    all_results_df,
                    x=param_names[0],
                    y=param_names[1],
                    z="Rendimento della strategia (%)",
                    color="Rendimento della strategia (%)",
                    title=f"Rendimento vs {param_names[0]} e {param_names[1]}"
                )
            elif selected_viz == "Surface 3D":
                # Crea una griglia per la superficie
                df_pivot = all_results_df.pivot_table(
                    index=param_names[0], 
                    columns=param_names[1], 
                    values="Rendimento della strategia (%)"
                )
                
                # Crea la superficie 3D
                fig = go.Figure(data=[go.Surface(
                    z=df_pivot.values,
                    x=df_pivot.index,
                    y=df_pivot.columns,
                    colorscale='Viridis'
                )])
                
                fig.update_layout(
                    title=f"Superficie di Rendimento: {param_names[0]} vs {param_names[1]}",
                    scene=dict(
                        xaxis_title=param_names[0],
                        yaxis_title=param_names[1],
                        zaxis_title="Rendimento (%)"
                    )
                )
            else:  # Heatmap
                # Crea una heatmap
                df_pivot = all_results_df.pivot_table(
                    index=param_names[0], 
                    columns=param_names[1], 
                    values="Rendimento della strategia (%)"
                )
                
                fig = px.imshow(
                    df_pivot,
                    labels=dict(x=param_names[1], y=param_names[0], color="Rendimento (%)"),
                    x=df_pivot.columns,
                    y=df_pivot.index,
                    color_continuous_scale="Viridis",
                    title=f"Heatmap di Rendimento: {param_names[0]} vs {param_names[1]}"
                )
                
                # Aggiungi annotazioni con i valori
                annotations = []
                for i, y in enumerate(df_pivot.index):
                    for j, x in enumerate(df_pivot.columns):
                        value = df_pivot.iloc[i, j]
                        if not pd.isna(value):  # Verifica che il valore non sia NaN
                            annotations.append(
                                dict(
                                    x=x,
                                    y=y,
                                    text=f"{value:.2f}",
                                    showarrow=False,
                                    font=dict(color="white" if abs(value) > 10 else "black")
                                )
                            )
                
                fig.update_layout(annotations=annotations)
            
            st.plotly_chart(fig, use_container_width=True)

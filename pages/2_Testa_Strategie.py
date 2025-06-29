# BorsaNew_app/pages/2_Testa_Strategie.py

# Fix NumPy 2.0+ compatibility
import numpy as np
if not hasattr(np, 'NaN'):
    np.NaN = np.nan

import streamlit as st
import pandas as pd
import datetime
import sys
import os

# Assicurati che il percorso radice del progetto sia nel sys.path
# Questo è fondamentale per importare correttamente da 'utils'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importa le funzioni dai moduli di utilità
from utils.importazione_dati import load_tickers_from_csv, download_stock_data, get_ticker_list_for_selection, extract_symbol_from_selection
from utils.strategies_config import STRATEGIE_DISPONIBILI
from utils.backtesting_engine import run_backtest
from utils.plotting_utils import plot_backtest_results, plot_equity_curves

# Per importare dinamicamente le classi delle strategie
import importlib

# --- Configurazione della pagina Streamlit ---
st.set_page_config(
    page_title="Testa Strategie",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Testa le tue Strategie di Trading")
st.markdown("Seleziona una strategia, configura i suoi parametri e i parametri di backtest per valutarne la performance.")

# --- Caricamento dei ticker disponibili dal CSV ---
tickers_file_path = "tickers.csv" # Assicurati che questo percorso sia corretto rispetto alla root del progetto
tickers_for_selection = get_ticker_list_for_selection(tickers_file_path)

# --- Input Utente ---
with st.sidebar:
    st.header("Configurazione Dati e Strategia")

    selected_ticker_display = st.selectbox(
        "Seleziona un Titolo Azionario:",
        options=tickers_for_selection
    )
    ticker_symbol = extract_symbol_from_selection(selected_ticker_display)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Data Inizio:", datetime.date(2022, 1, 1))
    with col2:
        end_date = st.date_input("Data Fine:", datetime.date.today())

    st.subheader("Selezione Strategia")
    selected_strategy_name = st.selectbox(
        "Scegli la Strategia:",
        options=list(STRATEGIE_DISPONIBILI.keys())
    )

    # Recupera i dettagli della strategia selezionata da STRATEGIE_DISPONIBILI
    strategy_info = STRATEGIE_DISPONIBILI.get(selected_strategy_name)
    strategy_parameters = {}

    if strategy_info:
        st.markdown(f"**Descrizione:** {strategy_info['description']}")
        st.subheader("Parametri della Strategia")
        for param_name, param_details in strategy_info['parameters'].items():
            param_type = param_details['type']
            default_value = param_details['default']
            min_value = param_details['min_value']
            max_value = param_details['max_value']
            step = param_details['step']
            label = param_details['label']

            if param_type == "int":
                strategy_parameters[param_name] = st.slider(
                    label,
                    min_value=min_value,
                    max_value=max_value,
                    value=default_value,
                    step=step,
                    key=f"param_{param_name}" # Chiave univoca per il widget
                )
            elif param_type == "float":
                strategy_parameters[param_name] = st.slider(
                    label,
                    min_value=float(min_value),
                    max_value=float(max_value),
                    value=float(default_value),
                    step=float(step),
                    key=f"param_{param_name}"
                )
    else:
        st.warning("Seleziona una strategia per visualizzarne i parametri.")

    # --- SEZIONE PER IL BACKTEST DELLA STRATEGIA ---
    st.header("Configurazione e Esecuzione Backtest")

    st.subheader("Parametri di Capitale e Trading")
    col_init_1, col_init_2 = st.columns(2)
    with col_init_1:
        initial_capital = st.number_input(
            "Capitale Iniziale (€)",
            min_value=100.0, value=10000.0, step=100.0,
            help="Il capitale con cui iniziare il backtest."
        )
    with col_init_2:
        investimento_fisso_per_trade = st.number_input(
            "Importo Fisso per Trade (€)",
            min_value=0.0, value=5000.0, step=100.0,
            help="L'importo specifico da investire per ogni singolo trade (long o short). Imposta a 0 per usare una percentuale del capitale disponibile."
        )

    col_trade_1, col_trade_2 = st.columns(2)
    with col_trade_1:
        commissione_percentuale = st.number_input(
            "Commissione per Trade (%)",
            min_value=0.0, max_value=5.0, value=0.2, step=0.01, format="%.2f",
            help="Percentuale di commissione applicata per ogni trade (acquisto/vendita)."
        )
    with col_trade_2:
        abilita_short = st.checkbox(
            "Abilita Trading Short",
            value=False,
            help="Consente alla strategia di aprire posizioni short."
        )

    # Nuovi parametri di gestione del rischio
    st.markdown("**Gestione del Rischio (Lascia vuoto per disabilitare)**")
    col9, col10, col11 = st.columns(3)
    with col9:
        stop_loss_percent = st.number_input("Stop Loss (%):", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.1f")
        if stop_loss_percent == 0.0: stop_loss_percent = None # Interpreta 0 come disabilitato
    with col10:
        take_profit_percent = st.number_input("Take Profit (%):", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.1f")
        if take_profit_percent == 0.0: take_profit_percent = None # Interpreta 0 come disabilitato
    with col11:
        trailing_stop_percent = st.number_input("Trailing Stop (%):", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.1f")
        if trailing_stop_percent == 0.0: trailing_stop_percent = None # Interpreta 0 come disabilitato

    run_button = st.button("Esegui Backtest", type="primary")

# --- Logica di Esecuzione del Backtest ---
if run_button:
    if start_date >= end_date:
        st.error("Errore: La data di inizio deve essere precedente alla data di fine.")
    else:
        with st.spinner("Scaricamento dati e esecuzione backtest..."):
            # 1. Scarica i dati
            data = download_stock_data(ticker_symbol, start_date, end_date)

            if isinstance(data, pd.DataFrame) and not data.empty:
                st.success("Dati scaricati con successo!")

                # --- LA VERA SOLUZIONE: REPLICA ESATTAMENTE LA LOGICA DI 1_Analisi_Tecnica.py ---
                if isinstance(data.columns, pd.MultiIndex):
                    # Estrai solo il primo livello del MultiIndex (es. 'Close' da ('Close', 'AAPL'))
                    data.columns = data.columns.get_level_values(0)

                # Standardizza i nomi delle colonne: converti in maiuscolo e rimuovi spazi
                # Questo è sicuro perché il MultiIndex è stato appiattito in un Index di stringhe
                data.columns = [col.upper().replace(' ', '') for col in data.columns]

                # Rinomina 'ADJCLOSE' in 'CLOSE' se presente (importante per consistenza con gli indicatori)
                if 'ADJCLOSE' in data.columns and 'CLOSE' not in data.columns:
                    data.rename(columns={'ADJCLOSE': 'CLOSE'}, inplace=True)
                # --- FINE LOGICA DI GESTIONE COLONNE ---

                # Assicurati che le colonne OHLCV richieste siano presenti
                required_cols = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
                if not all(col in data.columns for col in required_cols):
                    st.error(f"Il DataFrame non contiene tutte le colonne OHLCV richieste. Colonne presenti: {data.columns.tolist()}")
                else:
                    # 2. Inizializza e genera i segnali dalla strategia
                    try:
                        strategy_module = importlib.import_module(f"utils.logica_strategie.{strategy_info['module']}")
                        strategy_class = getattr(strategy_module, strategy_info['class'])

                        # Crea un'istanza della classe della strategia con i dati e i parametri
                        strategy_instance = strategy_class(df=data, **strategy_parameters)
                        df_with_signals = strategy_instance.generate_signals()

                        if df_with_signals.empty:
                            st.warning("Nessun segnale generato dalla strategia. Prova a modificare i parametri o l'intervallo di date.")
                        else:
                            st.success("Segnali di trading generati!")

                            # --- DEBUG: Visualizza i segnali generati ---
                            st.subheader("Debug: Segnali Generati")
                            
                            # Crea una copia del DataFrame per non modificare l'originale
                            debug_df = df_with_signals.copy()
                            
                            # Formatta la colonna Date per mostrare solo la data
                            if 'Date' in debug_df.columns:
                                debug_df['Date'] = pd.to_datetime(debug_df['Date']).dt.strftime('%Y-%m-%d')
                            elif isinstance(debug_df.index, pd.DatetimeIndex):
                                debug_df.index = debug_df.index.strftime('%Y-%m-%d')
                            
                            # Aggiungi la colonna Status
                            debug_df['Status'] = 'No Position'
                            current_position = 0
                            
                            for idx in range(len(debug_df)):
                                if debug_df.iloc[idx]['Signal'] == 1:  # Buy signal
                                    current_position = 1
                                elif debug_df.iloc[idx]['Signal'] == -1:  # Sell signal
                                    current_position = -1
                                
                                if current_position == 1:
                                    debug_df.iloc[idx, debug_df.columns.get_loc('Status')] = 'Long'
                                elif current_position == -1:
                                    debug_df.iloc[idx, debug_df.columns.get_loc('Status')] = 'Short'
                            
                            # Mostra tutti i record con segnali
                            st.write("Tutti i segnali generati:")
                            st.dataframe(debug_df)
                            
                            # Mostra statistiche sui segnali
                            signals_summary = debug_df[debug_df['Signal'] != 0]
                            if not signals_summary.empty:
                                st.write(f"Numero totale di segnali BUY: {signals_summary[signals_summary['Signal'] == 1].shape[0]}")
                                st.write(f"Numero totale di segnali SELL: {signals_summary[signals_summary['Signal'] == -1].shape[0]}")
                            else:
                                st.info("Nessun segnale BUY (1) o SELL (-1) significativo generato dalla strategia nel periodo.")
                            
                            # --- FINE DEBUG ---

                            # --- Adattamento per backtesting_engine che si aspetta 'Close' (Title Case) ---
                            # Crea una copia per evitare di modificare df_with_signals se usato altrove dopo
                            df_for_backtest = df_with_signals.copy()
                            if 'CLOSE' in df_for_backtest.columns:
                                df_for_backtest.rename(columns={'CLOSE': 'Close'}, inplace=True)
                            if 'OPEN' in df_for_backtest.columns:
                                df_for_backtest.rename(columns={'OPEN': 'Open'}, inplace=True)
                            if 'HIGH' in df_for_backtest.columns:
                                df_for_backtest.rename(columns={'HIGH': 'High'}, inplace=True)
                            if 'LOW' in df_for_backtest.columns:
                                df_for_backtest.rename(columns={'LOW': 'Low'}, inplace=True)
                            if 'VOLUME' in df_for_backtest.columns:
                                df_for_backtest.rename(columns={'VOLUME': 'Volume'}, inplace=True)
                            # --- Fine Adattamento ---
                            # Esegui il backtest
                            trade_log, equity_curve, buy_hold_equity_series, metrics = run_backtest(
                                dati=df_for_backtest,
                                capitale_iniziale=initial_capital,
                                commissione_percentuale=commissione_percentuale,
                                abilita_short=abilita_short,
                                investimento_fisso_per_trade=investimento_fisso_per_trade if investimento_fisso_per_trade > 0 else None,
                                stop_loss_percent=stop_loss_percent,
                                take_profit_percent=take_profit_percent,
                                trailing_stop_percent=trailing_stop_percent
                            )
                            if not trade_log:
                                st.warning("Nessun trade eseguito durante il backtest con i parametri specificati.")
                            else:
                                st.success(f"Backtest completato! Eseguiti {len(trade_log)} trade.")

                                # --- Dettaglio dei Trade con motivo di chiusura ---
                                st.subheader("Dettaglio dei Trade Eseguiti")
                                trades_df = pd.DataFrame(trade_log)
                                
                                # Aggiungi una colonna per il motivo della chiusura
                                trades_df['Motivo'] = trades_df['Tipo'].apply(lambda x: 
                                    'Apertura Posizione Long' if x == 'BUY' else
                                    'Chiusura Posizione Long' if x == 'SELL' else
                                    'Apertura Posizione Short' if x == 'SELL SHORT' else
                                    'Chiusura Posizione Short' if x == 'COVER' else
                                    'Chiusura Finale Long' if x == 'SELL (Chiusura Finale LONG)' else
                                    'Chiusura Finale Short' if x == 'COVER (Chiusura Finale SHORT)' else
                                    'Stop Loss' if 'Stop Loss' in x else
                                    'Take Profit' if 'Take Profit' in x else
                                    'Trailing Stop' if 'Trailing Stop' in x else
                                    'Segnale Opposto' if ('SELL' in x and 'LONG' in x) or ('COVER' in x and 'SHORT' in x) else
                                    x
                                )
                                
                                # Formatta le date
                                trades_df['Data'] = pd.to_datetime(trades_df['Data']).dt.date
                                
                                # Riorganizza le colonne per una migliore visualizzazione
                                column_order = ['Data', 'Tipo', 'Motivo', 'Prezzo', 'Quantità', 'P/L (€)', 'Equity (€)']
                                trades_df = trades_df[column_order + [col for col in trades_df.columns if col not in column_order]]
                                
                                st.dataframe(trades_df)
                                
                                # Mostra statistiche sui motivi di chiusura
                                st.write("Statistiche sui motivi di chiusura:")
                                closure_stats = trades_df['Motivo'].value_counts()
                                st.write(closure_stats)

                                # 4. Visualizza le metriche (già calcolate in 'metrics')
                                st.subheader("Metriche di Performance")
                                
                                # Calcola metriche aggiuntive
                                total_commission = sum(trade.get('Comm. (€)', 0) for trade in trade_log)
                                winning_trades = len([t for t in trade_log if t.get('P/L (€)', 0) > 0])
                                losing_trades = len([t for t in trade_log if t.get('P/L (€)', 0) < 0])
                                win_rate = (winning_trades / len(trade_log) * 100) if trade_log else 0
                                
                                # Calcola Profit Factor
                                gross_profit = sum(t.get('P/L (€)', 0) for t in trade_log if t.get('P/L (€)', 0) > 0)
                                gross_loss = abs(sum(t.get('P/L (€)', 0) for t in trade_log if t.get('P/L (€)', 0) < 0))
                                profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
                                
                                # Calcola Reward/Risk Ratio
                                avg_win = gross_profit / winning_trades if winning_trades > 0 else 0
                                avg_loss = gross_loss / losing_trades if losing_trades > 0 else 0
                                reward_risk_ratio = avg_win / avg_loss if avg_loss != 0 else float('inf')
                                
                                # Calcola Buy & Hold Return
                                buy_hold_return = ((buy_hold_equity_series.iloc[-1] / initial_capital) - 1) * 100
                                
                                # Crea il dizionario delle metriche nell'ordine richiesto
                                metriche_risultati = {
                                    'Nome del Titolo': selected_ticker_display,
                                    'Nome della Strategia': selected_strategy_name,
                                    'Data Iniziale del Test': start_date.strftime('%Y-%m-%d'),
                                    'Data Finale del Test': end_date.strftime('%Y-%m-%d'),
                                    'Commissione (%)': commissione_percentuale,
                                    'Abilita Short': 'Sì' if abilita_short else 'No',
                                    'Importo Fisso per Trade (€)': investimento_fisso_per_trade if investimento_fisso_per_trade > 0 else 'N/A',
                                    'Stop Loss (%)': stop_loss_percent if stop_loss_percent is not None else 'N/A',
                                    'Take Profit (%)': take_profit_percent if take_profit_percent is not None else 'N/A',
                                    'Trailing Stop (%)': trailing_stop_percent if trailing_stop_percent is not None else 'N/A',
                                    'Parametri della Strategia Testata': str(strategy_parameters),
                                    'Capitale Iniziale (€)': round(initial_capital, 2),
                                    'Capitale Finale (€)': round(metrics['Capitale Finale (€)'], 2),
                                    'Profitto/Perdita Totale netto (€)': round(metrics['Profitto/Perdita Totale (€)'], 2),
                                    'Profitto/Perdita Totale netto (%)': round(metrics['Profitto/Perdita Totale (%)'], 2),
                                    'Giorni Totali': metrics.get('Giorni Totali', 0),
                                    'Rendimento Medio Annuale (%)': round(metrics['Rendimento Medio Annuale (%)'], 2),
                                    'Spese di Commissione Totali (€)': round(total_commission, 2),
                                    'Numero Totale di Trade': metrics['Numero Totale di Trade'],
                                    'Num. Trade Long': metrics['Num. Trade Long'],
                                    'P/L Medio Trade Long (%)': round(metrics['P/L Medio Trade Long (%)'], 2),
                                    'Num. Trade Short': metrics['Num. Trade Short'],
                                    'P/L Medio Trade Short (%)': round(metrics['P/L Medio Trade Short (%)'], 2),
                                    'Num. Trade Vincenti': metrics['Num. Trade Vincenti'],
                                    'Num. Trade Perdenti': metrics['Num. Trade Perdenti'],
                                    'Percentuale Trade Vincenti': round(metrics['Percentuale Trade Vincenti'], 2),
                                    'Profitto Medio Trade Vincenti (€)': round(metrics['Profitto Medio Trade Vincenti (€)'], 2),
                                    'Profitto Medio Trade Vincenti (%)': round(metrics['Profitto Medio Trade Vincenti (%)'], 2),
                                    'Perdita Media Trade Perdenti (€)': round(metrics['Perdita Media Trade Perdenti (€)'], 2),
                                    'Perdita Media Trade Perdenti (%)': round(metrics['Perdita Media Trade Perdenti (%)'], 2),
                                    'Profitto Massimo Trade (€)': round(metrics['Profitto Massimo Trade (€)'], 2),
                                    'Profitto Massimo Trade (%)': round(metrics['Profitto Massimo Trade (%)'], 2),
                                    'Data Profitto Massimo': metrics['Data Profitto Massimo'],
                                    'Perdita Massima Trade (€)': round(metrics['Perdita Massima Trade (€)'], 2),
                                    'Perdita Massima Trade (%)': round(metrics['Perdita Massima Trade (%)'], 2),
                                    'Data Perdita Massima': metrics['Data Perdita Massima'],
                                    'Durata Media Trade (giorni)': round(metrics['Durata Media Trade (giorni)'], 1),
                                    'Profit Factor': round(profit_factor, 2),
                                    'Reward/Risk Ratio': round(reward_risk_ratio, 2),
                                    'Max Drawdown (€)': round(metrics['Max Drawdown (€)'], 2),
                                    'Max Drawdown (%)': round(metrics['Max Drawdown (%)'], 2),
                                    'Ratio Sharpe': round(metrics['Ratio Sharpe'], 2),
                                    'Ratio Sortino': round(metrics['Ratio Sortino'], 2),
                                    'Ratio Calmar': round(metrics['Ratio Calmar'], 2),
                                    'Buy & Hold Return (%)': round(buy_hold_return, 2)
                                }
                                
                                # Visualizza le metriche in una tabella
                                metrics_df = pd.DataFrame([metriche_risultati]).T.rename(columns={0: "Valore"})
                                st.dataframe(metrics_df)

                                # 6. Visualizza Equity Curve
                                st.subheader("Andamento del Capitale (Equity Curve)")
                                plot_equity_fig = plot_equity_curves(equity_curve, buy_hold_equity_series)
                                st.plotly_chart(plot_equity_fig, use_container_width=True)

                                # 7. Visualizza grafico con indicatori e trade markers
                                st.subheader("Grafico dei Prezzi con Segnali e Trade")

                                indicator_cols_to_plot = []
                                if selected_strategy_name == "CCI-SMA":
                                    indicator_cols_to_plot = ['CCI', 'SMA']
                                elif selected_strategy_name == "Incrocio Medie Mobili":
                                    indicator_cols_to_plot = ['SMA_Short', 'SMA_Long']
                                elif selected_strategy_name == "Livelli Bollinger":
                                    indicator_cols_to_plot = ['BBL', 'BBM', 'BBU']
                                elif selected_strategy_name == "Livelli Stocastico (DIFF D-DD)":
                                    indicator_cols_to_plot = ['%K', '%D', '%DD']

                                # Adatta il formato dei trade per il plotting
                                adapted_trades = []
                                for i, trade in enumerate(trade_log):
                                    # Determina la data di uscita dal trade successivo se disponibile
                                    exit_date = None
                                    exit_price = None
                                    
                                    # Se è un trade di apertura (BUY o SHORT), cerca la data di chiusura
                                    if 'BUY' in trade['Tipo'] or 'SHORT' in trade['Tipo']:
                                        if i < len(trade_log) - 1:
                                            for j in range(i+1, len(trade_log)):
                                                if ('SELL' in trade_log[j]['Tipo'] and 'BUY' in trade['Tipo']) or \
                                                   ('COVER' in trade_log[j]['Tipo'] and 'SHORT' in trade['Tipo']):
                                                    exit_date = trade_log[j]['Data']
                                                    exit_price = trade_log[j]['Prezzo']
                                                    break
                                    
                                    # Determina il motivo di chiusura per il trade
                                    exit_reason = None
                                    
                                    # Estrai il motivo di chiusura dal tipo di trade
                                    if 'Stop Loss' in trade.get('Tipo', ''):
                                        exit_reason = 'Stop Loss'
                                    elif 'Take Profit' in trade.get('Tipo', ''):
                                        exit_reason = 'Take Profit'
                                    elif 'Trailing Stop' in trade.get('Tipo', ''):
                                        exit_reason = 'Trailing Stop'
                                    
                                    # Determina il tipo di trade
                                    if 'BUY' in trade['Tipo']:
                                        trade_type = 'LONG'
                                    elif 'SHORT' in trade['Tipo']:
                                        trade_type = 'SHORT'
                                    elif 'SELL' in trade['Tipo']:
                                        trade_type = 'SELL'
                                    elif 'COVER' in trade['Tipo']:
                                        trade_type = 'COVER'
                                    else:
                                        trade_type = 'UNKNOWN'
                                    
                                    adapted_trade = {
                                        'entry_date': trade['Data'],
                                        'entry_price': trade['Prezzo'],
                                        'exit_date': exit_date,
                                        'exit_price': exit_price,
                                        'exit_reason': exit_reason,
                                        'trade_type': trade_type,
                                        'status': 'Closed' if exit_date is not None else 'Open' if ('BUY' in trade['Tipo'] or 'SHORT' in trade['Tipo']) else 'Closed',
                                        'profit/loss_%': trade.get('P/L (€)', 0) / (trade['Prezzo'] * trade['Quantità']) * 100 if 'P/L (€)' in trade else 0
                                    }
                                    adapted_trades.append(adapted_trade)

                                # Crea un dizionario per i marker di Stop Loss, Take Profit e Trailing Stop
                                sl_markers = []
                                tp_markers = []
                                ts_markers = []
                                
                                # Identifica i trade con Stop Loss, Take Profit e Trailing Stop
                                for trade in trade_log:
                                    trade_type = trade.get('Tipo', '')
                                    if 'Stop Loss' in trade_type:
                                        sl_markers.append({
                                            'date': pd.to_datetime(trade['Data']),
                                            'price': trade['Prezzo']
                                        })
                                    elif 'Take Profit' in trade_type:
                                        tp_markers.append({
                                            'date': pd.to_datetime(trade['Data']),
                                            'price': trade['Prezzo']
                                        })
                                    elif 'Trailing Stop' in trade_type:
                                        ts_markers.append({
                                            'date': pd.to_datetime(trade['Data']),
                                            'price': trade['Prezzo']
                                        })
                                
                                # Aggiungi i marker direttamente al DataFrame
                                if sl_markers or tp_markers or ts_markers:
                                    df_with_signals = df_with_signals.copy()
                                    
                                    # Aggiungi colonne per i marker
                                    df_with_signals['SL_Marker'] = None
                                    df_with_signals['TP_Marker'] = None
                                    df_with_signals['TS_Marker'] = None
                                    
                                    # Aggiungi i marker di Stop Loss
                                    for marker in sl_markers:
                                        if marker['date'] in df_with_signals.index:
                                            df_with_signals.at[marker['date'], 'SL_Marker'] = marker['price']
                                    
                                    # Aggiungi i marker di Take Profit
                                    for marker in tp_markers:
                                        if marker['date'] in df_with_signals.index:
                                            df_with_signals.at[marker['date'], 'TP_Marker'] = marker['price']
                                    
                                    # Aggiungi i marker di Trailing Stop
                                    for marker in ts_markers:
                                        if marker['date'] in df_with_signals.index:
                                            df_with_signals.at[marker['date'], 'TS_Marker'] = marker['price']
                                
                                # Debug dei marker
                                st.write("Debug dei marker:")
                                if 'SL_Marker' in df_with_signals.columns:
                                    sl_markers = df_with_signals[df_with_signals['SL_Marker'].notnull()]
                                    st.write(f"Stop Loss markers: {len(sl_markers)}")
                                if 'TP_Marker' in df_with_signals.columns:
                                    tp_markers = df_with_signals[df_with_signals['TP_Marker'].notnull()]
                                    st.write(f"Take Profit markers: {len(tp_markers)}")
                                if 'TS_Marker' in df_with_signals.columns:
                                    ts_markers = df_with_signals[df_with_signals['TS_Marker'].notnull()]
                                    st.write(f"Trailing Stop markers: {len(ts_markers)}")
                                
                                price_chart_fig = plot_backtest_results(
                                    dati_con_indicatori=df_with_signals,
                                    lista_dei_trade=adapted_trades,
                                    ticker=ticker_symbol,
                                    nome_esteso=selected_ticker_display,
                                    plotly_dragmode="zoom",
                                    indicator_cols_to_plot=indicator_cols_to_plot
                                )
                                st.plotly_chart(price_chart_fig, use_container_width=True)

                    except Exception as e:
                        st.error(f"Errore durante l'esecuzione della strategia o del backtest: {e}")
                        st.exception(e)
            else:
                st.warning("Impossibile scaricare i dati o i dati sono vuoti per il simbolo e l'intervallo specificati. Riprova con altre selezioni.")
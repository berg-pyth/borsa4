 # Borsa2_app/pages/1_Analisi_Tecnica.py

import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

# Assicurati che il percorso radice del progetto sia nel sys.path
# Questo è fondamentale per importare correttamente da 'utils'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importa le funzioni dai moduli di utilità
from utils.importazione_dati import load_tickers_from_csv, download_stock_data, get_ticker_list_for_selection, extract_symbol_from_selection
# Importa il modulo completo di calcolo degli indicatori per un'importazione più pulita
import utils.calcolo_indicatori as ci # Ho usato 'ci' come alias per brevità

# --- Configurazione della pagina Streamlit ---
st.set_page_config(
    page_title="Analisi Tecnica",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Analisi Tecnica dei Titoli Azionari")
st.markdown("Seleziona un titolo e un intervallo di date per visualizzare i dati storici e gli indicatori.")

# --- Caricamento dei ticker disponibili dal CSV ---
tickers_file_path = "tickers.csv" # Assicurati che questo percorso sia corretto rispetto a dove esegui l'app
available_tickers_display = get_ticker_list_for_selection(tickers_file_path)

if not available_tickers_display:
    st.error("Impossibile caricare i simboli dei titoli dal file 'tickers.csv'. Assicurati che il file esista e sia formattato correttamente nella root del progetto.")
    st.stop() # Ferma l'esecuzione se non ci sono ticker da selezionare

# --- Sidebar per l'input utente ---
st.sidebar.header("Impostazioni Titolo e Periodo")

# Selezione del titolo azionario
selected_ticker_display = st.sidebar.selectbox(
    "Seleziona un titolo:",
    options=available_tickers_display,
    key="ticker_select"
)

# Estrai il simbolo effettivo dal display string
selected_ticker_symbol = extract_symbol_from_selection(selected_ticker_display)

# Selezione del periodo di date
today = datetime.date.today()
default_start_date = today - datetime.timedelta(days=365 * 2) # Due anni fa come default

col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Data Inizio", value=default_start_date, key="start_date_input")
end_date = col2.date_input("Data Fine", value=today, key="end_date_input")

if start_date >= end_date:
    st.sidebar.error("La data di inizio deve essere precedente alla data di fine.")
    # Non st.stop() qui, permettiamo all'utente di correggere senza ricaricare

# --- Logica di caricamento dati (Spostato fuori dal bottone per reattività) ---
df_data = None
if selected_ticker_symbol and start_date < end_date:
    # Aggiungi un messaggio di caricamento
    with st.spinner(f"Caricamento dati per {selected_ticker_symbol} dal {start_date} al {end_date}..."):
        df_data = download_stock_data(selected_ticker_symbol, start_date, end_date)

    if df_data is not None and not df_data.empty:
        # --- Gestione del MultiIndex e standardizzazione dei nomi delle colonne ---
        if isinstance(df_data.columns, pd.MultiIndex):
            df_data.columns = df_data.columns.get_level_values(0)
        
        # Standardizza i nomi delle colonne: converti in maiuscolo e rimuovi spazi
        df_data.columns = [col.upper().replace(' ', '') for col in df_data.columns]

        # Rinomina 'ADJCLOSE' in 'CLOSE' se presente
        if 'ADJCLOSE' in df_data.columns and 'CLOSE' not in df_data.columns:
            df_data.rename(columns={'ADJCLOSE': 'CLOSE'}, inplace=True)
        
        required_cols_upper = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
        missing_cols = [col for col in required_cols_upper if col not in df_data.columns]
        if missing_cols:
            st.error(f"Dati mancanti: le seguenti colonne necessarie non sono state trovate nel DataFrame dopo la standardizzazione: {', '.join(missing_cols)}. Colonne disponibili: {', '.join(df_data.columns)}")
            df_data = None # Imposta df_data a None per evitare errori a cascata
    else:
        st.warning(f"Nessun dato disponibile per {selected_ticker_symbol} nel periodo selezionato.")
        df_data = None # Imposta df_data a None per evitare errori a cascata

# --- Blocco principale dell'applicazione solo se i dati sono stati caricati con successo ---
if df_data is not None and not df_data.empty:
    st.subheader(f"Dati Storici per {selected_ticker_symbol}")

    # --- Tabella Dati Grezzi ---
    st.write("### Dati Grezzi (Tutti i record)")
    # Mostra solo le colonne OHLCV (usando i nomi standardizzati in maiuscolo)
    cols_to_display = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
    df_display_table = df_data[cols_to_display].copy()
    df_display_table.index = df_display_table.index.strftime('%Y-%m-%d')
    st.dataframe(df_display_table.style.format("{:.2f}"))

    st.subheader("Configurazione e Visualizzazione Indicatori Tecnici")

    # NUOVA OPZIONE: Scelta del tipo di grafico per il prezzo
    st.sidebar.header("Opzioni Grafico Prezzo")
    price_chart_type = st.sidebar.radio(
        "Seleziona tipo di grafico prezzo:",
        ("Candlestick", "Linea di Chiusura"),
        key="price_chart_type_select"
    )

    # Definisce gli indicatori disponibili e i loro parametri di default
    # Utilizziamo l'alias 'ci' per richiamare le funzioni dal modulo utils.calcolo_indicatori
    available_indicators = {
        "SMA": {"func": ci.calculate_sma, "params": {"period": 20}, "plot_type": "overlay"},
        "EMA": {"func": ci.calculate_ema, "params": {"period": 20}, "plot_type": "overlay"},
        "RSI": {"func": ci.calculate_rsi, "params": {"period": 14}, "plot_type": "separate"},
        "Stocastico": {"func": ci.calculate_stochastic, "params": {"k_period": 14, "d_period": 3}, "plot_type": "separate"},
        "Bande di Bollinger": {"func": ci.calculate_bollinger_bands, "params": {"length": 20, "std": 2}, "plot_type": "overlay"},
        "CCI": {"func": ci.calculate_cci, "params": {"length": 20}, "plot_type": "separate"},
        "ROC": {"func": ci.calculate_roc, "params": {"length": 10}, "plot_type": "separate"},
        "Supertrend": {"func": ci.calculate_supertrend, "params": {"period": 10, "multiplier": 3.0}, "plot_type": "overlay"},
        # Aggiungi qui gli altri indicatori che hai creato, usando 'ci.' come prefisso
    }

    st.sidebar.header("Indicatori Tecnici")
    selected_indicators_names = st.sidebar.multiselect(
        "Seleziona gli indicatori (max 4)",
        list(available_indicators.keys()),
        default=[],
        key="indicator_multiselect"
    )

    if len(selected_indicators_names) > 4:
        st.sidebar.warning("Puoi selezionare un massimo di 4 indicatori.")
        selected_indicators_names = selected_indicators_names[:4]

    calculated_indicators = {}
    indicator_subplots_names = [] # Nomi degli indicatori da plottare in subplots separati

    for ind_name in selected_indicators_names:
        st.sidebar.subheader(f"Parametri {ind_name}")
        indicator_info = available_indicators[ind_name]
        params = indicator_info["params"].copy() # Copia per non modificare il default

        # Crea gli slider o number_input per i parametri dell'indicatore
        for param_name, default_value in params.items():
            if param_name in ["period", "length", "k_period", "d_period"]:
                params[param_name] = st.sidebar.slider(
                    f"{param_name.replace('_', ' ').title()} {ind_name}",
                    min_value=1,
                    max_value=200,
                    value=default_value,
                    key=f"{ind_name}_{param_name}"
                )
            elif param_name == "std":
                params[param_name] = st.sidebar.slider(
                    f"{param_name.replace('_', ' ').title()} {ind_name}",
                    min_value=0.5, # Può essere float
                    max_value=5.0,
                    value=float(default_value), # Assicurati che sia float
                    step=0.1,
                    key=f"{ind_name}_{param_name}"
                )
        
        try:
            # Gestione speciale per gli indicatori che richiedono high, low, close
            if ind_name in ["Stocastico", "CCI", "Supertrend"]:
                if all(col in df_data.columns for col in ['HIGH', 'LOW', 'CLOSE']):
                    calculated_value = indicator_info["func"](df_data["HIGH"], df_data["LOW"], df_data["CLOSE"], **params)
                else:
                    st.warning(f"Colonne HIGH, LOW o CLOSE mancanti per il calcolo di {ind_name}.")
                    continue # Salta il calcolo di questo indicatore
            else:
                # Per SMA, EMA, RSI, Bande di Bollinger, ROC che usano solo la chiusura
                if 'CLOSE' in df_data.columns:
                    calculated_value = indicator_info["func"](df_data["CLOSE"], **params)
                else:
                    st.warning(f"Colonna CLOSE mancante per il calcolo di {ind_name}.")
                    continue # Salta il calcolo di questo indicatore

            calculated_indicators[ind_name] = calculated_value
            if indicator_info["plot_type"] == "separate":
                indicator_subplots_names.append(ind_name)

        except Exception as e:
            st.error(f"Errore nel calcolo di {ind_name}: {e}")
            st.exception(e) # Mostra i dettagli dell'errore per il debug

    # --- Plotting dei Prezzi e Indicatori ---
    num_indicator_subplots = len(indicator_subplots_names)
    total_rows = 1 + num_indicator_subplots # 1 per il prezzo/volume, il resto per gli indicatori separati

    # Definisce le altezze delle righe per i subplots
    # Prima riga (prezzo) più grande, il resto equamente distribuiti
    row_heights_list = [0.5] # Altezza per il plot del prezzo
    if num_indicator_subplots > 0:
        row_heights_list.extend([(0.5 / num_indicator_subplots) for _ in range(num_indicator_subplots)])

    fig = make_subplots(
        rows=total_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05, # Riduci lo spazio verticale
        row_heights=row_heights_list
    )

    # Plot del prezzo (Candlestick o Linea di Chiusura)
    if price_chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(x=df_data.index,
                                     open=df_data['OPEN'],
                                     high=df_data['HIGH'],
                                     low=df_data['LOW'],
                                     close=df_data['CLOSE'],
                                     name='Prezzo Candele'), row=1, col=1)
    else: # Linea di Chiusura
        fig.add_trace(go.Scatter(x=df_data.index,
                                 y=df_data['CLOSE'],
                                 mode='lines',
                                 name='Prezzo Chiusura',
                                 line=dict(color='blue', width=2)), row=1, col=1)


    # Aggiungi gli indicatori che si sovrappongono al plot del prezzo (es. medie mobili, Bande di Bollinger)
    for ind_name in selected_indicators_names:
        indicator_info = available_indicators.get(ind_name)
        if indicator_info and indicator_info["plot_type"] == "overlay" and ind_name in calculated_indicators:
            if ind_name == "Bande di Bollinger" and isinstance(calculated_indicators[ind_name], pd.DataFrame):
                bb_data = calculated_indicators[ind_name]
                # Le bande di Bollinger hanno tre linee
                fig.add_trace(go.Scatter(
                    x=bb_data.index,
                    y=bb_data.iloc[:, 0], # Banda Inferiore (BBL)
                    mode='lines',
                    name=f'{ind_name} Lower',
                    line=dict(width=1, color='orange')
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=bb_data.index,
                    y=bb_data.iloc[:, 1], # Banda Media (BBM)
                    mode='lines',
                    name=f'{ind_name} Middle',
                    line=dict(width=1, color='blue', dash='dash')
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=bb_data.index,
                    y=bb_data.iloc[:, 2], # Banda Superiore (BBU)
                    mode='lines',
                    name=f'{ind_name} Upper',
                    line=dict(width=1, color='orange')
                ), row=1, col=1)
            elif ind_name == "Supertrend" and isinstance(calculated_indicators[ind_name], pd.DataFrame):
                st_data = calculated_indicators[ind_name]
                # Aggiungi le linee del Supertrend (trend rialzista in verde, ribassista in rosso)
                fig.add_trace(go.Scatter(
                    x=st_data.index,
                    y=st_data['up_trend'],
                    mode='lines',
                    name=f'{ind_name} Up',
                    line=dict(width=2, color='green'),
                    connectgaps=False
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(
                    x=st_data.index,
                    y=st_data['down_trend'],
                    mode='lines',
                    name=f'{ind_name} Down',
                    line=dict(width=2, color='red'),
                    connectgaps=False
                ), row=1, col=1)
            else:
                # Per SMA/EMA o altri overlay singoli
                fig.add_trace(go.Scatter(
                    x=calculated_indicators[ind_name].index,
                    y=calculated_indicators[ind_name],
                    mode='lines',
                    name=f'{ind_name} ({indicator_info["params"].get("period", indicator_info["params"].get("length", ""))})',
                    line=dict(width=1)
                ), row=1, col=1)


    # Plot degli indicatori in subplots separati
    current_row = 2
    for ind_name in indicator_subplots_names:
        indicator_value = calculated_indicators[ind_name]
        indicator_info = available_indicators[ind_name]

        if ind_name == "Stocastico" and isinstance(indicator_value, pd.DataFrame):
            # Lo Stocastico restituisce un DataFrame con %K e %D
            # Utilizziamo la ricerca delle colonne più robusta, basata sull'output di pandas_ta
            k_cols = [col for col in indicator_value.columns if 'Stoch_%K' in col]
            d_cols = [col for col in indicator_value.columns if 'Stoch_%D' in col]

            if k_cols and d_cols: # Assicurati che le liste non siano vuote prima di accedere all'elemento
                fig.add_trace(go.Scatter(
                    x=indicator_value.index,
                    y=indicator_value[k_cols[0]], # Accede tramite il nome della colonna trovato
                    mode='lines',
                    name=f'{ind_name} %K',
                    line=dict(width=1)
                ), row=current_row, col=1)
                fig.add_trace(go.Scatter(
                    x=indicator_value.index,
                    y=indicator_value[d_cols[0]], # Accede tramite il nome della colonna trovato
                    mode='lines',
                    name=f'{ind_name} %D',
                    line=dict(width=1)
                ), row=current_row, col=1)
                fig.add_hline(y=80, line_dash="dot", line_color="red", row=current_row, col=1)
                fig.add_hline(y=20, line_dash="dot", line_color="green", row=current_row, col=1)
            else:
                st.warning(f"Impossibile trovare le colonne '%K' o '%D' per lo Stocastico nel grafico. Colonne disponibili: {indicator_value.columns.tolist()}")


        elif ind_name == "RSI" and isinstance(indicator_value, pd.Series):
            fig.add_trace(go.Scatter(
                x=indicator_value.index,
                y=indicator_value,
                mode='lines',
                name=f'{ind_name} ({indicator_info["params"].get("period", "")})',
                line=dict(width=1)
            ), row=current_row, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="red", row=current_row, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=current_row, col=1)
        
        elif ind_name == "CCI" and isinstance(indicator_value, pd.Series):
            fig.add_trace(go.Scatter(
                x=indicator_value.index,
                y=indicator_value,
                mode='lines',
                name=f'{ind_name} ({indicator_info["params"].get("length", "")})',
                line=dict(width=1)
            ), row=current_row, col=1)
            fig.add_hline(y=100, line_dash="dot", line_color="red", row=current_row, col=1)
            fig.add_hline(y=-100, line_dash="dot", line_color="green", row=current_row, col=1)

        elif ind_name == "ROC" and isinstance(indicator_value, pd.Series):
            fig.add_trace(go.Scatter(
                x=indicator_value.index,
                y=indicator_value,
                mode='lines',
                name=f'{ind_name} ({indicator_info["params"].get("length", "")})',
                line=dict(width=1)
            ), row=current_row, col=1)
            fig.add_hline(y=0, line_dash="dash", line_color="grey", row=current_row, col=1)

        else: # Tutti gli altri indicatori che restituiscono una singola serie e vanno in subplot separato
            if isinstance(indicator_value, pd.Series):
                fig.add_trace(go.Scatter(
                    x=indicator_value.index,
                    y=indicator_value,
                    mode='lines',
                    name=f'{ind_name} ({indicator_info["params"].get("period", indicator_info["params"].get("length", ""))})',
                    line=dict(width=1)
                ), row=current_row, col=1)


        fig.update_yaxes(title_text=ind_name, row=current_row, col=1) # Titolo per l'asse Y di ogni indicatore
        fig.update_xaxes(showticklabels=False, row=current_row, col=1) # Nascondi etichette X per subplots
        fig.update_yaxes(showgrid=True, zeroline=False, row=current_row, col=1) # Griglia per indicatori
        current_row += 1


    fig.update_layout(
        title_text=f'{selected_ticker_symbol} Analisi Tecnica Dettagliata',
        xaxis_rangeslider_visible=False, # Nasconde il range slider sotto il grafico principale
        height=800, # Altezza totale del grafico con tutti i subplots
        margin=dict(t=50, b=0, l=0, r=0),
        hovermode="x unified"
    )

    # Aggiorna gli assi X e Y per il plot principale
    fig.update_xaxes(showgrid=True, zeroline=False, row=1, col=1) # Mostra griglia solo sul grafico principale
    fig.update_yaxes(title_text='Prezzo', row=1, col=1, showgrid=True, zeroline=False)

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Dati Tabulati degli Indicatori (Tutti i record)")
    if calculated_indicators:
        # Crea un DataFrame con tutti i dati necessari per la tabella
        df_display_indicators = df_data[['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']].copy()
        
        for ind_name, series_or_df in calculated_indicators.items():
            if isinstance(series_or_df, pd.Series):
                df_display_indicators[f"{ind_name}"] = series_or_df
            elif isinstance(series_or_df, pd.DataFrame):
                # Per indicatori come lo Stocastico e le Bande di Bollinger che restituiscono un DataFrame
                # Renaming delle colonne per un display più pulito
                if ind_name == "Stocastico":
                    # Utilizziamo la ricerca delle colonne più robusta, basata sull'output di pandas_ta
                    k_cols = [col for col in series_or_df.columns if 'Stoch_%K' in col]
                    d_cols = [col for col in series_or_df.columns if 'Stoch_%D' in col]

                    if k_cols and d_cols: # Assicurati che le liste non siano vuote prima di accedere all'elemento
                        df_display_indicators[f"Stocastico_%K"] = series_or_df[k_cols[0]]
                        df_display_indicators[f"Stocastico_%D"] = series_or_df[d_cols[0]]
                    else:
                        st.warning(f"Impossibile trovare le colonne '%K' o '%D' per lo Stocastico nella tabella. Colonne disponibili: {series_or_df.columns.tolist()}")

                elif ind_name == "Bande di Bollinger":
                    # Usa i nomi delle colonne già puliti che abbiamo impostato in calculate_bollinger_bands
                    for col in series_or_df.columns:
                        df_display_indicators[col] = series_or_df[col]
                else: # fallback per altri casi di DataFrame multi-output
                    for col_name in series_or_df.columns:
                        df_display_indicators[f"{ind_name}_{col_name}"] = series_or_df[col_name]
        
        df_display_indicators.index = df_display_indicators.index.strftime('%Y-%m-%d')
        st.dataframe(df_display_indicators.round(2)) # Rimosso .tail(30)
    else:
        st.info("Seleziona uno o più indicatori per visualizzare i loro dati tabulati.")

else:
    st.info("Seleziona un titolo e un intervallo di date, poi il grafico apparirà qui.")
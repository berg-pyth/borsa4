# plotting_utils

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime # Importa il modulo datetime per Timedelta
import sys # Importa sys per le stampe di debug

def plot_backtest_results(
    dati_con_indicatori: pd.DataFrame,
    lista_dei_trade: list,
    ticker: str,
    nome_esteso: str,
    plotly_dragmode: str,
    indicator_cols_to_plot: list[str]
) -> go.Figure:
    """
    Genera un grafico Plotly interattivo con la linea dei prezzi di chiusura e i marker dei trade.
    """
    if dati_con_indicatori.empty:
        fig = go.Figure()
        fig.update_layout(title_text="Nessun dato disponibile per la visualizzazione.")
        return fig

    # Debug: stampa il tipo e la struttura dei dati
    print("Tipo di lista_dei_trade:", type(lista_dei_trade))
    print("Primi 3 trade:", lista_dei_trade[:3] if len(lista_dei_trade) >= 3 else lista_dei_trade)

    # Classifica gli indicatori in overlay (sul grafico principale) e oscillatori (in subplot)
    overlay_indicators = []
    oscillator_indicators = []
    
    for indicator in indicator_cols_to_plot:
        # Indicatori che vanno sul grafico principale (overlay)
        if any(x in indicator.upper() for x in ['SMA', 'EMA', 'BBL', 'BBM', 'BBU', 'VWAP']):
            overlay_indicators.append(indicator)
        # Oscillatori che vanno in un subplot separato
        else:
            oscillator_indicators.append(indicator)
    
    # Determina il numero di righe necessarie per i subplot
    n_rows = 1 + (1 if oscillator_indicators else 0)
    
    # Crea i subplot
    fig = make_subplots(
        rows=n_rows, 
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3] if n_rows > 1 else [1]
    )

    # Crea una lista di colori per ogni punto del prezzo - sempre blu quando non ci sono operazioni aperte
    colors = ['blue'] * len(dati_con_indicatori)
    current_position = None
    current_position_start = None

    # Determina i colori basati sulle posizioni aperte
    # Ordina i trade per data di entrata
    sorted_trades = sorted(lista_dei_trade, key=lambda x: pd.to_datetime(x['entry_date']))
    
    for trade in sorted_trades:
        try:
            entry_date = pd.to_datetime(trade['entry_date'])
            trade_type = trade['trade_type']
            status = trade['status']

            if status == 'Open':
                # Trova l'indice della data di ingresso
                try:
                    entry_idx = dati_con_indicatori.index.get_loc(entry_date)
                    current_position = trade_type
                    current_position_start = entry_idx
                except KeyError:
                    print(f"Data di ingresso {entry_date} non trovata nell'indice")
                    continue

            elif status == 'Closed':
                # Trova l'indice della data di uscita
                exit_date = pd.to_datetime(trade.get('exit_date', entry_date))
                try:
                    exit_idx = dati_con_indicatori.index.get_loc(exit_date)
                except KeyError:
                    # Se la data di uscita non è nell'indice, usa l'ultimo indice disponibile
                    exit_idx = len(dati_con_indicatori) - 1
                
                # Colora il periodo della posizione solo se è un'apertura
                if trade_type in ['LONG', 'SHORT']:
                    color = 'green' if trade_type == 'LONG' else 'red'
                    # Trova l'indice di inizio (dalla data di entrata)
                    try:
                        start_idx = dati_con_indicatori.index.get_loc(entry_date)
                        # Colora solo fino all'indice di uscita
                        for i in range(start_idx, exit_idx + 1):
                            if i < len(colors):  # Verifica che l'indice sia valido
                                colors[i] = color
                    except KeyError:
                        print(f"Data di ingresso {entry_date} non trovata nell'indice")
                        continue

        except Exception as e:
            print(f"Errore nel processare il trade {trade}: {str(e)}")
            continue

    # Se c'è una posizione aperta alla fine, colora fino alla fine
    if current_position is not None and current_position_start is not None:
        color = 'green' if current_position == 'LONG' else 'red'
        for i in range(current_position_start, len(colors)):
            colors[i] = color

    # Crea segmenti di linea con colori diversi
    prev_color = colors[0]
    prev_idx = 0
    
    for i in range(1, len(colors)):
        if colors[i] != prev_color:
            # Aggiungi il segmento con il colore precedente
            fig.add_trace(go.Scatter(
                x=dati_con_indicatori.index[prev_idx:i],
                y=dati_con_indicatori['CLOSE'][prev_idx:i],
                mode='lines',
                name='Prezzo di Chiusura',
                line=dict(color=prev_color, width=2),
                showlegend=False
            ), row=1, col=1)
            prev_color = colors[i]
            prev_idx = i
    
    # Aggiungi l'ultimo segmento
    fig.add_trace(go.Scatter(
        x=dati_con_indicatori.index[prev_idx:],
        y=dati_con_indicatori['CLOSE'][prev_idx:],
        mode='lines',
        name='Prezzo di Chiusura',
        line=dict(color=prev_color, width=2),
        showlegend=False
    ), row=1, col=1)

    # Debug: stampa i trade per verificare la struttura
    print("DEBUG - Verifica trade per markers:")
    for i, trade in enumerate(lista_dei_trade):
        print(f"Trade {i}: {trade}")
    
    # Verifica se ci sono marker di Stop Loss, Take Profit e Trailing Stop nel DataFrame
    sl_dates = []
    sl_prices = []
    tp_dates = []
    tp_prices = []
    ts_dates = []
    ts_prices = []
    
    # Verifica se le colonne dei marker esistono
    if 'SL_Marker' in dati_con_indicatori.columns:
        # Estrai i marker di Stop Loss
        sl_markers = dati_con_indicatori[dati_con_indicatori['SL_Marker'].notnull()]
        if not sl_markers.empty:
            sl_dates = sl_markers.index.tolist()
            sl_prices = sl_markers['SL_Marker'].tolist()
            print(f"DEBUG - Trovati {len(sl_dates)} marker di Stop Loss")
    
    if 'TP_Marker' in dati_con_indicatori.columns:
        # Estrai i marker di Take Profit
        tp_markers = dati_con_indicatori[dati_con_indicatori['TP_Marker'].notnull()]
        if not tp_markers.empty:
            tp_dates = tp_markers.index.tolist()
            tp_prices = tp_markers['TP_Marker'].tolist()
            print(f"DEBUG - Trovati {len(tp_dates)} marker di Take Profit")
    
    if 'TS_Marker' in dati_con_indicatori.columns:
        # Estrai i marker di Trailing Stop
        ts_markers = dati_con_indicatori[dati_con_indicatori['TS_Marker'].notnull()]
        if not ts_markers.empty:
            ts_dates = ts_markers.index.tolist()
            ts_prices = ts_markers['TS_Marker'].tolist()
            print(f"DEBUG - Trovati {len(ts_dates)} marker di Trailing Stop")
    
    # Aggiungi i marker per le chiusure
    if sl_dates:
        fig.add_trace(go.Scatter(
            x=sl_dates,
            y=sl_prices,
            mode='markers',
            marker=dict(color='red', size=10, symbol='circle'),
            name='Stop Loss',
            hoverinfo='text',
            hovertext=[f'Stop Loss: {price:.2f}' if price is not None else 'Stop Loss' for price in sl_prices]
        ), row=1, col=1)
    
    if tp_dates:
        fig.add_trace(go.Scatter(
            x=tp_dates,
            y=tp_prices,
            mode='markers',
            marker=dict(color='green', size=10, symbol='circle'),
            name='Take Profit',
            hoverinfo='text',
            hovertext=[f'Take Profit: {price:.2f}' if price is not None else 'Take Profit' for price in tp_prices]
        ), row=1, col=1)
    
    if ts_dates:
        fig.add_trace(go.Scatter(
            x=ts_dates,
            y=ts_prices,
            mode='markers',
            marker=dict(color='yellow', size=10, symbol='circle'),
            name='Trailing Stop',
            hoverinfo='text',
            hovertext=[f'Trailing Stop: {price:.2f}' if price is not None else 'Trailing Stop' for price in ts_prices]
        ), row=1, col=1)
    
    # Aggiungi le tracce per la legenda
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='lines',
        line=dict(color='green', width=2),
        name='Posizione LONG Aperta'
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='lines',
        line=dict(color='red', width=2),
        name='Posizione SHORT Aperta'
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='lines',
        line=dict(color='blue', width=2),
        name='Nessuna Posizione'
    ), row=1, col=1)
    
    # Aggiungi gli indicatori overlay al grafico principale
    for indicator in overlay_indicators:
        if indicator in dati_con_indicatori.columns:
            fig.add_trace(go.Scatter(
                x=dati_con_indicatori.index,
                y=dati_con_indicatori[indicator],
                mode='lines',
                name=indicator,
                line=dict(width=1.5)
            ), row=1, col=1)
    
    # Aggiungi gli oscillatori in un subplot separato
    if oscillator_indicators and n_rows > 1:
        for indicator in oscillator_indicators:
            if indicator in dati_con_indicatori.columns:
                fig.add_trace(go.Scatter(
                    x=dati_con_indicatori.index,
                    y=dati_con_indicatori[indicator],
                    mode='lines',
                    name=indicator,
                    line=dict(width=1.5)
                ), row=2, col=1)

    # --- Configurazione del layout del grafico ---
    fig.update_layout(
        title_text=f"Backtest per {nome_esteso} ({ticker})",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        dragmode=plotly_dragmode,
        height=800 if n_rows > 1 else 600,
        template="plotly_dark",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )

    # Aggiorna gli assi
    fig.update_xaxes(
        showgrid=True,
        zeroline=True,
        rangeslider_visible=False
    )
    
    # Configura l'asse Y principale
    fig.update_yaxes(
        title_text="Prezzo",
        showgrid=True,
        zeroline=True,
        row=1, col=1
    )
    
    # Configura l'asse Y per gli oscillatori
    if n_rows > 1:
        fig.update_yaxes(
            title_text="Oscillatori",
            showgrid=True,
            zeroline=True,
            row=2, col=1
        )

    return fig


def plot_equity_curves(strategy_equity: pd.Series, buy_hold_equity: pd.Series) -> go.Figure:
    """
    Genera un grafico Plotly che confronta l'equity curve della strategia
    con quella di un approccio Buy & Hold.

    Args:
        strategy_equity (pd.Series): Serie pandas dell'equity curve della strategia.
        buy_hold_equity (pd.Series): Serie pandas dell'equity curve Buy & Hold normalizzata.

    Returns:
        go.Figure: L'oggetto figura Plotly con le due equity curve.
    """
    fig = go.Figure()

    # Aggiungi la traccia per l'equity della strategia
    if not strategy_equity.empty:
        fig.add_trace(go.Scatter(
            x=strategy_equity.index,
            y=strategy_equity.values,
            mode='lines',
            name='Strategia',
            line=dict(color='blue')
        ))

    # Aggiungi la traccia per l'equity del Buy & Hold
    if not buy_hold_equity.empty:
         fig.add_trace(go.Scatter(
             x=buy_hold_equity.index,
             y=buy_hold_equity.values,
             mode='lines',
             name='Buy & Hold',
             line=dict(color='green', dash='dash')
         ))


    # Configura il layout del grafico
    fig.update_layout(
        title_text='Confronto Equity Curve: Strategia vs Buy & Hold',
        xaxis_title='Data',
        yaxis_title='Valore Equity (Normalizzato)',
        hovermode='x unified',
        template="plotly_dark",
        legend=dict(x=0.01, y=0.99, xanchor='left', yanchor='top')
    )

    fig.update_xaxes(showgrid=True, zeroline=True)
    fig.update_yaxes(showgrid=True, zeroline=True)

    return fig
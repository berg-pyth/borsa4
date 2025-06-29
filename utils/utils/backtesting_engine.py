# backtesting_engine.py

import pandas as pd
import numpy as np
from pandas import Timestamp
from datetime import date
import datetime # Importa il modulo datetime per Timedelta

def run_backtest(
    dati: pd.DataFrame, # DataFrame con dati OHLCV, Indicatori, e colonna 'Signal'
    capitale_iniziale: float,
    commissione_percentuale: float,
    abilita_short: bool,
    investimento_fisso_per_trade: float = None, # Nuovo parametro: importo fisso per ogni trade
    stop_loss_percent: float = None, # None se non abilitato
    take_profit_percent: float = None, # None se non abilitato
    trailing_stop_percent: float = None, # None se non abilitato
    # Puoi aggiungere altri parametri qui se necessario in futuro (es. slippage)
) -> tuple[list, pd.Series, pd.Series, dict]:
    """
    Esegue il backtest di una strategia di trading sui dati forniti.

    Args:
        dati (pd.DataFrame): DataFrame con dati storici (OHLCV) e colonna 'Signal' generata dalla strategia.
        capitale_iniziale (float): Capitale iniziale per il backtest.
        commissione_percentuale (float): Percentuale di commissione per operazione (ingresso e uscita).
        abilita_short (bool): Se true, le posizioni Short sono permesse.
        investimento_fisso_per_trade (float, optional): Importo fisso da investire per ogni trade.
                                                        Se None o 0, usa una percentuale di capitale.
        stop_loss_percent (float, optional): Percentuale di stop loss dal prezzo di ingresso.
                                             Es. 1.0 per 1%. None se non abilitato.
        take_profit_percent (float, optional): Percentuale di take profit dal prezzo di ingresso.
                                               Es. 2.0 per 2%. None se non abilitato.
        trailing_stop_percent (float, optional): Percentuale di trailing stop. Es. 0.5 per 0.5%. None se non abilitato.

    Returns:
        tuple[list, pd.Series, pd.Series, dict]: Una tupla contenente:
            - trade_log (list): Lista di dizionari che rappresentano ogni trade eseguito.
            - equity_curve (pd.Series): Serie temporale del capitale totale (equity) nel tempo.
            - buy_hold_equity_series (pd.Series): Serie temporale del capitale se avessi fatto Buy & Hold.
            - metriche_risultati (dict): Dizionario delle metriche di performance del backtest.
    """
    capital_available = capitale_iniziale
    in_position = False
    shares_held = 0
    entry_price = 0
    trade_log = []
    equity_curve_values = []
    daily_returns = pd.Series(dtype=float) # Per calcolare lo Sharpe Ratio

    # Inizializzazione per Stop Loss / Take Profit / Trailing Stop
    stop_loss_price = None
    take_profit_price = None
    trailing_stop_highest_price = None # Per posizioni LONG
    trailing_stop_lowest_price = None # Per posizioni SHORT

    # Verifica che la colonna 'Signal' esista
    if 'Signal' not in dati.columns:
        raise ValueError("Il DataFrame dati deve contenere una colonna 'Signal'.")

    # Assicurati che l'indice sia un DatetimeIndex per lavorare correttamente con le date
    if not isinstance(dati.index, pd.DatetimeIndex):
        dati.index = pd.to_datetime(dati.index)

    # Inizializza l'equity curve con il capitale iniziale
    equity_curve_values.append(capitale_iniziale)
    
    previous_day_capital = capitale_iniziale # Per calcolo dei rendimenti giornalieri

    for i, (index, row) in enumerate(dati.iterrows()):
        current_close = row['Close']
        current_open = row['Open']
        current_high = row['High']
        current_low = row['Low']
        current_signal = row['Signal']
        
        # Calcola il capitale corrente (equity) prima di processare i segnali del giorno
        # Equity = capitale disponibile + valore delle azioni detenute (che può essere negativo per short)
        if shares_held > 0:  # Posizione LONG
            current_equity = capital_available + (shares_held * current_close)
        elif shares_held < 0:  # Posizione SHORT
            # Per posizioni SHORT, il profitto è la differenza tra prezzo di entrata e prezzo corrente
            unrealized_pnl = abs(shares_held) * (entry_price - current_close)
            # Per le posizioni short, il capitale disponibile include il capitale bloccato come garanzia
            current_equity = capital_available + unrealized_pnl
        else:  # Nessuna posizione
            current_equity = capital_available
        equity_curve_values.append(current_equity)

        # Calcolo del rendimento giornaliero per lo Sharpe Ratio
        if previous_day_capital != 0:
            daily_return = (current_equity - previous_day_capital) / previous_day_capital
            daily_returns = pd.concat([daily_returns, pd.Series([daily_return], index=[index])])
        previous_day_capital = current_equity


        # Gestione dei segnali di trading
        if not in_position:  # Se non siamo in posizione
            if current_signal == 1:  # Segnale BUY
                # Calcola il numero di azioni da acquistare
                if investimento_fisso_per_trade is not None and investimento_fisso_per_trade > 0:
                    shares_to_buy = int(investimento_fisso_per_trade / current_close)
                else:
                    shares_to_buy = int(capital_available * 0.95 / current_close)  # Usa il 95% del capitale disponibile

                if shares_to_buy > 0: 
                    cost = shares_to_buy * current_close * (1 + commissione_percentuale / 100)
                    commission = (shares_to_buy * current_close * commissione_percentuale) / 100
                    
                    if cost <= capital_available:
                        capital_available -= cost
                        shares_held = shares_to_buy
                        entry_price = current_close
                        in_position = True
                        
                        # Imposta Stop Loss / Take Profit / Trailing Stop per LONG
                        stop_loss_price = entry_price * (1 - stop_loss_percent / 100) if stop_loss_percent is not None else None
                        take_profit_price = entry_price * (1 + take_profit_percent / 100) if take_profit_percent is not None else None
                        trailing_stop_highest_price = current_high if trailing_stop_percent is not None else None
                        
                        trade_log.append({
                            'Data': index.date(),
                            'Tipo': 'BUY',
                            'Prezzo': current_close,
                            'Quantità': shares_to_buy,
                            'Costo': cost,
                            'Comm. (€)': commission,
                            'Equity (€)': current_equity
                        })

            elif current_signal == -1 and abilita_short:  # Segnale SELL (SHORT)
                # Calcola il numero di azioni da vendere allo scoperto
                if investimento_fisso_per_trade is not None and investimento_fisso_per_trade > 0:
                    shares_to_short = int(investimento_fisso_per_trade / current_close)
                else:
                    shares_to_short = int(capital_available * 0.95 / current_close)  # Usa il 95% del capitale disponibile

                if shares_to_short > 0:
                    # Per posizioni short, blocchiamo il 100% del valore come garanzia
                    cost = shares_to_short * current_close * (1 + commissione_percentuale / 100)
                    commission = (shares_to_short * current_close * commissione_percentuale) / 100
                    
                    if cost <= capital_available:
                        # Non sottraiamo il costo dal capitale disponibile per le posizioni short
                        # Il capitale rimane bloccato ma non viene sottratto
                        shares_held = -shares_to_short  # Negativo per indicare posizione SHORT
                        entry_price = current_close
                        in_position = True

                        # Imposta Stop Loss / Take Profit / Trailing Stop per SHORT
                        stop_loss_price = entry_price * (1 + stop_loss_percent / 100) if stop_loss_percent is not None else None
                        take_profit_price = entry_price * (1 - take_profit_percent / 100) if take_profit_percent is not None else None
                        trailing_stop_lowest_price = current_low if trailing_stop_percent is not None else None
                        
                        trade_log.append({
                            'Data': index.date(),
                            'Tipo': 'SELL SHORT',
                            'Prezzo': current_close,
                            'Quantità': shares_to_short,
                            'Costo': cost,
                            'Comm. (€)': commission,
                            'Equity (€)': current_equity
                        })

        elif in_position:  # Se siamo in posizione
            # Verifica Stop Loss, Take Profit e Trailing Stop
            exit_reason = None
            
            if shares_held > 0:  # Posizione LONG
                # Mantieni separati i livelli di stop loss fisso e trailing stop
                fixed_stop_loss = None
                trailing_stop = None
                
                # Imposta lo stop loss fisso se attivo
                if stop_loss_percent is not None:
                    fixed_stop_loss = entry_price * (1 - stop_loss_percent / 100)
                
                # Aggiorna il trailing stop se attivo
                if trailing_stop_percent is not None and trailing_stop_highest_price is not None:
                    # Aggiorna il prezzo più alto raggiunto
                    if current_high > trailing_stop_highest_price:
                        trailing_stop_highest_price = current_high
                        # Calcola il nuovo livello di trailing stop
                        trailing_stop = trailing_stop_highest_price * (1 - trailing_stop_percent / 100)
                
                # Verifica le condizioni di uscita
                if trailing_stop is not None and current_low <= trailing_stop:
                    exit_reason = f"SELL (Trailing Stop a {trailing_stop:.2f})"
                elif fixed_stop_loss is not None and current_low <= fixed_stop_loss:
                    exit_reason = f"SELL (Stop Loss a {fixed_stop_loss:.2f})"
                elif take_profit_price is not None and current_high >= take_profit_price:
                    exit_reason = f"SELL (Take Profit a {take_profit_price:.2f})"
            
            elif shares_held < 0:  # Posizione SHORT
                # Mantieni separati i livelli di stop loss fisso e trailing stop
                fixed_stop_loss = None
                trailing_stop = None
                
                # Imposta lo stop loss fisso se attivo
                if stop_loss_percent is not None:
                    fixed_stop_loss = entry_price * (1 + stop_loss_percent / 100)
                
                # Aggiorna il trailing stop se attivo
                if trailing_stop_percent is not None and trailing_stop_lowest_price is not None:
                    # Aggiorna il prezzo più basso raggiunto
                    if current_low < trailing_stop_lowest_price:
                        trailing_stop_lowest_price = current_low
                        # Calcola il nuovo livello di trailing stop
                        trailing_stop = trailing_stop_lowest_price * (1 + trailing_stop_percent / 100)
                
                # Verifica le condizioni di uscita
                if trailing_stop is not None and current_high >= trailing_stop:
                    exit_reason = f"COVER (Trailing Stop a {trailing_stop:.2f})"
                elif fixed_stop_loss is not None and current_high >= fixed_stop_loss:
                    exit_reason = f"COVER (Stop Loss a {fixed_stop_loss:.2f})"
                elif take_profit_price is not None and current_low <= take_profit_price:
                    exit_reason = f"COVER (Take Profit a {take_profit_price:.2f})"
            
            # Esegui l'uscita se è stato attivato uno stop
            if exit_reason:
                if shares_held > 0:  # Chiudi posizione LONG
                    revenue = shares_held * current_close * (1 - commissione_percentuale / 100)
                    commission = (shares_held * current_close * commissione_percentuale) / 100
                    profit_loss = revenue - (shares_held * entry_price)
                    capital_available += revenue
                    
                    trade_log.append({
                        'Data': index.date(),
                        'Tipo': exit_reason,
                        'Prezzo': current_close,
                        'Quantità': shares_held,
                        'Ricavo': revenue,
                        'Comm. (€)': commission,
                        'P/L (€)': profit_loss,
                        'Equity (€)': current_equity
                    })
                else:  # Chiudi posizione SHORT
                    cost_to_close = abs(shares_held) * current_close * (1 + commissione_percentuale / 100)
                    commission = (abs(shares_held) * current_close * commissione_percentuale) / 100
                    profit_loss = (abs(shares_held) * entry_price) - (abs(shares_held) * current_close)
                    
                    trade_log.append({
                        'Data': index.date(),
                        'Tipo': exit_reason,
                        'Prezzo': current_close,
                        'Quantità': abs(shares_held),
                        'Costo Chiusura Short': cost_to_close,
                        'Comm. (€)': commission,
                        'P/L (€)': profit_loss,
                        'Equity (€)': current_equity
                    })
                
                # Reset delle variabili di posizione
                shares_held = 0
                entry_price = 0
                in_position = False
                stop_loss_price = None
                take_profit_price = None
                trailing_stop_highest_price = None
                trailing_stop_lowest_price = None
            
            # Verifica segnali di inversione solo se non è già stata chiusa la posizione per stop/target
            elif (shares_held > 0 and current_signal == -1) or (shares_held < 0 and current_signal == 1):
                # Chiudi la posizione esistente
                if shares_held > 0:  # Chiudi posizione LONG
                    revenue = shares_held * current_close * (1 - commissione_percentuale / 100)
                    commission = (shares_held * current_close * commissione_percentuale) / 100
                    profit_loss = revenue - (shares_held * entry_price)
                    capital_available += revenue
                    
                    trade_log.append({
                        'Data': index.date(),
                        'Tipo': 'SELL',
                        'Prezzo': current_close,
                        'Quantità': shares_held,
                        'Ricavo': revenue,
                        'Comm. (€)': commission,
                        'P/L (€)': profit_loss,
                        'Equity (€)': current_equity
                    })
                else:  # Chiudi posizione SHORT
                    cost_to_close = abs(shares_held) * current_close * (1 + commissione_percentuale / 100)
                    commission = (abs(shares_held) * current_close * commissione_percentuale) / 100
                    profit_loss = (abs(shares_held) * entry_price) - (abs(shares_held) * current_close)
                    
                    trade_log.append({
                        'Data': index.date(),
                        'Tipo': 'COVER',
                        'Prezzo': current_close,
                        'Quantità': abs(shares_held),
                        'Costo Chiusura Short': cost_to_close,
                        'Comm. (€)': commission,
                        'P/L (€)': profit_loss,
                        'Equity (€)': current_equity
                    })
                
                # Reset delle variabili di posizione
                shares_held = 0
                entry_price = 0
                in_position = False  # IMPORTANTE: Imposta in_position a False dopo la chiusura
                stop_loss_price = None
                take_profit_price = None
                trailing_stop_highest_price = None
                trailing_stop_lowest_price = None

                # Se c'è un segnale di inversione, apri subito la nuova posizione
                if current_signal == -1 and abilita_short:  # Apri posizione SHORT
                    shares_to_short = int(capital_available * 0.95 / current_close)
                    if shares_to_short > 0:
                        cost = shares_to_short * current_close * (1 + commissione_percentuale / 100)
                        commission = (shares_to_short * current_close * commissione_percentuale) / 100
                        
                        if cost <= capital_available:
                            shares_held = -shares_to_short
                            entry_price = current_close
                            in_position = True

                            if stop_loss_percent is not None:
                                stop_loss_price = entry_price * (1 + stop_loss_percent / 100)
                            if take_profit_percent is not None:
                                take_profit_price = entry_price * (1 - take_profit_percent / 100)
                            if trailing_stop_percent is not None:
                                trailing_stop_lowest_price = current_low
                            
                            trade_log.append({
                                'Data': index.date(),
                                'Tipo': 'SELL SHORT',
                                'Prezzo': current_close,
                                'Quantità': shares_to_short,
                                'Costo': cost,
                                'Comm. (€)': commission,
                                'Equity (€)': current_equity
                            })
                elif current_signal == 1:  # Apri posizione LONG
                    shares_to_buy = int(capital_available * 0.95 / current_close)
                    if shares_to_buy > 0:
                        cost = shares_to_buy * current_close * (1 + commissione_percentuale / 100)
                        commission = (shares_to_buy * current_close * commissione_percentuale) / 100
                        
                        if cost <= capital_available:
                            capital_available -= cost
                            shares_held = shares_to_buy
                            entry_price = current_close
                            in_position = True

                            if stop_loss_percent is not None:
                                stop_loss_price = entry_price * (1 - stop_loss_percent / 100)
                            if take_profit_percent is not None:
                                take_profit_price = entry_price * (1 + take_profit_percent / 100)
                            if trailing_stop_percent is not None:
                                trailing_stop_highest_price = current_high
                            
                            trade_log.append({
                                'Data': index.date(),
                                'Tipo': 'BUY',
                                'Prezzo': current_close,
                                'Quantità': shares_to_buy,
                                'Costo': cost,
                                'Comm. (€)': commission,
                                'Equity (€)': current_equity
                            })

    # Chiudi le posizioni aperte alla fine del backtest
    if in_position:
        # Verifica che la colonna 'Close' esista e che il DataFrame non sia vuoto
        if 'Close' in dati.columns and not dati.empty:
            final_price = dati['Close'].iloc[-1]
            if shares_held > 0: # Posizione LONG aperta
                revenue_final = shares_held * final_price * (1 - commissione_percentuale / 100)
                commission_final = (shares_held * final_price * commissione_percentuale) / 100
                profit_loss_final = revenue_final - (shares_held * entry_price)
                
                capital_available += revenue_final

                print(f"DEBUG FINAL SELL LONG: Tipo di final_price: {type(final_price)}, Valore: {final_price}") # DEBUG PRINT
                trade_log.append({
                    'Data': dati.index[-1].date(),
                    'Tipo': 'SELL (Chiusura Finale LONG)',
                    'Prezzo': final_price,
                    'Quantità': shares_held,
                    'Ricavo': revenue_final,
                    'Comm. (€)': commission_final,
                    'P/L (€)': profit_loss_final,
                    'Equity (€)': current_equity
                })
        elif shares_held < 0 and 'Close' in dati.columns and not dati.empty: # Posizione SHORT aperta
            final_price = dati['Close'].iloc[-1]
            cost_to_cover_final = abs(shares_held) * final_price * (1 + commissione_percentuale / 100)
            commission_final_short = (abs(shares_held) * final_price * commissione_percentuale) / 100
            profit_loss_final_short = (abs(shares_held) * entry_price) - (abs(shares_held) * final_price)
            
            capital_available -= cost_to_cover_final

            print(f"DEBUG FINAL COVER SHORT: Tipo di final_price: {type(final_price)}, Valore: {final_price}") # DEBUG PRINT
            trade_log.append({
                'Data': dati.index[-1].date(),
                'Tipo': 'COVER (Chiusura Finale SHORT)',
                'Prezzo': final_price,
                'Quantità': abs(shares_held),
                'Costo Chiusura Short': cost_to_cover_final,
                'Comm. (€)': commission_final_short,
                'P/L (€)': profit_loss_final_short,
                'Equity (€)': current_equity
            })

    # Calcola le metriche di performance
    # Crea una Serie pandas per l'equity curve
    equity_curve = pd.Series(equity_curve_values, index=[dati.index[0]] + list(dati.index))
    if len(equity_curve) > len(dati.index): # Rimuovi il primo elemento duplicato se l'equity curve è stata inizializzata con il capitale iniziale
        equity_curve = equity_curve.iloc[1:]
    
    # Assicurati che l'equity curve abbia la stessa lunghezza dell'indice dei dati
    # A volte equity_curve_values può avere un elemento in più dovuto all'inizializzazione o al conteggio.
    # Questo allineamento è cruciale per i calcoli giornalieri e per evitare errori.
    if len(equity_curve) != len(dati.index):
        # Questo è un caso limite, assicurarsi che l'equity_curve abbia la lunghezza corretta
        # Ad esempio, se l'equity_curve_values ha N+1 elementi (capitale iniziale + N giorni)
        # e dati.index ha N elementi.
        if len(equity_curve_values) == len(dati.index) + 1:
            equity_curve = pd.Series(equity_curve_values[1:], index=dati.index)
        elif len(equity_curve_values) == len(dati.index):
             equity_curve = pd.Series(equity_curve_values, index=dati.index)
        else:
             # Se le lunghezze non corrispondono ancora, potrebbe esserci un problema nella logica di append
             print(f"ATTENZIONE: Lunghezza equity_curve ({len(equity_curve_values)}) non corrisponde a dati.index ({len(dati.index)})")
             # Tentativo di allineamento, potrebbe portare a problemi se la discrepanza è complessa
             equity_curve = pd.Series(equity_curve_values[:len(dati.index)], index=dati.index)


    # Buy & Hold Equity Curve
    # Normalizza i prezzi di chiusura all'inizio del backtest
    buy_hold_prices = dati['Close']
    if not buy_hold_prices.empty and buy_hold_prices.iloc[0] != 0:
        buy_hold_equity_series = (buy_hold_prices / buy_hold_prices.iloc[0]) * capitale_iniziale
    else:
        buy_hold_equity_series = pd.Series([capitale_iniziale] * len(dati), index=dati.index)

    # Calcolo delle metriche
    # Prima contiamo i trade vincenti e perdenti
    winning_trades = [t for t in trade_log if 'P/L (€)' in t and t['P/L (€)'] > 0]
    losing_trades = [t for t in trade_log if 'P/L (€)' in t and t['P/L (€)'] < 0]
    num_winning_trades = len(winning_trades)
    num_losing_trades = len(losing_trades)
    # Il totale dei trade è la somma dei vincenti e perdenti
    total_trades = num_winning_trades + num_losing_trades

    # Calcola le statistiche per i trade Long e Short
    print("DEBUG: Tipi di trade nel log:")
    for trade in trade_log:
        print(f"Tipo: {trade.get('Tipo', 'N/A')}, P/L: {trade.get('P/L (€)', 'N/A')}")

    # Calcola le statistiche per i trade Long e Short
    long_trades = []
    short_trades = []
    
    for trade in trade_log:
        trade_type = trade.get('Tipo', '')
        if 'P/L (€)' in trade:
            if 'BUY' in trade_type or 'SELL' in trade_type or 'LONG' in trade_type:
                long_trades.append(trade)
            elif 'SHORT' in trade_type or 'COVER' in trade_type:
                short_trades.append(trade)
    
    num_long_trades = len(long_trades)
    num_short_trades = len(short_trades)
    
    print(f"DEBUG: Numero di trade long: {num_long_trades}")
    print(f"DEBUG: Numero di trade short: {num_short_trades}")
    
    # Calcola il P/L medio per i trade Long
    long_pnl_total = sum(t['P/L (€)'] for t in long_trades)
    avg_long_pnl_percent = (long_pnl_total / (num_long_trades * capitale_iniziale) * 100) if num_long_trades > 0 else 0
    
    # Calcola il P/L medio per i trade Short
    short_pnl_total = sum(t['P/L (€)'] for t in short_trades)
    avg_short_pnl_percent = (short_pnl_total / (num_short_trades * capitale_iniziale) * 100) if num_short_trades > 0 else 0

    # Verifica che il totale dei trade sia corretto
    total_trades = num_long_trades + num_short_trades
    if total_trades != num_winning_trades + num_losing_trades:
        print(f"ATTENZIONE: Discrepanza nel conteggio dei trade. Total: {total_trades}, Winning+Losing: {num_winning_trades + num_losing_trades}")
        # Usa il conteggio più accurato
        total_trades = num_winning_trades + num_losing_trades

    # Calcola il P/L totale come differenza tra capitale finale e iniziale
    total_pnl = current_equity - capitale_iniziale

    # Calcola il P&L totale in percentuale rispetto al capitale iniziale
    total_pnl_percent = (total_pnl / capitale_iniziale * 100) if capitale_iniziale != 0 else 0.0

    # Calcola il profitto medio dei trade vincenti
    avg_winning_trade = sum(t['P/L (€)'] for t in winning_trades) / num_winning_trades if num_winning_trades > 0 else 0
    avg_winning_trade_percent = (avg_winning_trade / capitale_iniziale * 100) if capitale_iniziale != 0 else 0

    # Calcola la perdita media dei trade perdenti
    avg_losing_trade = sum(t['P/L (€)'] for t in losing_trades) / num_losing_trades if num_losing_trades > 0 else 0
    avg_losing_trade_percent = (avg_losing_trade / capitale_iniziale * 100) if capitale_iniziale != 0 else 0

    # Trova il trade con il profitto massimo
    max_profit_trade = max(winning_trades, key=lambda x: x['P/L (€)']) if winning_trades else None
    max_profit = max_profit_trade['P/L (€)'] if max_profit_trade else 0
    max_profit_percent = (max_profit / capitale_iniziale * 100) if capitale_iniziale != 0 else 0
    max_profit_date = max_profit_trade['Data'] if max_profit_trade else None

    # Trova il trade con la perdita massima
    max_loss_trade = min(losing_trades, key=lambda x: x['P/L (€)']) if losing_trades else None
    max_loss = max_loss_trade['P/L (€)'] if max_loss_trade else 0
    max_loss_percent = (max_loss / capitale_iniziale * 100) if capitale_iniziale != 0 else 0
    max_loss_date = max_loss_trade['Data'] if max_loss_trade else None

    # Calcola la durata media dei trade
    trade_durations = []
    for i in range(0, len(trade_log)-1, 2):
        if i+1 < len(trade_log):
            entry_date = pd.to_datetime(trade_log[i]['Data'])
            exit_date = pd.to_datetime(trade_log[i+1]['Data'])
            duration = (exit_date - entry_date).days
            trade_durations.append(duration)
    avg_trade_duration = sum(trade_durations) / len(trade_durations) if trade_durations else 0

    # Calcola il profitto/perdita medio annuale
    total_days = (pd.to_datetime(dati.index[-1]) - pd.to_datetime(dati.index[0])).days
    annualized_return = (total_pnl / capitale_iniziale) * (365 / total_days) * 100 if capitale_iniziale != 0 and total_days > 0 else 0

    # Calcolo del Max Drawdown
    if not equity_curve.empty:
        # Calcola i massimi cumulativi dell'equity curve
        cumulative_max = equity_curve.cummax()
        # Calcola il drawdown in percentuale
        drawdown = (cumulative_max - equity_curve) / cumulative_max
        max_drawdown_percent = drawdown.max() * 100
        # Calcola il drawdown in valore assoluto (€)
        max_drawdown_abs = (cumulative_max - equity_curve).max()
    else:
        max_drawdown_percent = 0.0
        max_drawdown_abs = 0.0

    # Calcolo Sharpe Ratio
    # Assicurati che daily_returns non sia vuoto per evitare divisione per zero o errore di deviazione standard
    if not daily_returns.empty and daily_returns.std() != 0:
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) # 252 giorni di trading in un anno
        metriche_risultati = {'Ratio Sharpe': round(sharpe_ratio, 2)}
    else:
        metriche_risultati = {'Ratio Sharpe': 0.0}

    # Sortino Ratio
    # Solo i rendimenti negativi
    downside_returns = daily_returns[daily_returns < 0]
    if not downside_returns.empty and downside_returns.std() != 0:
        sortino_ratio = daily_returns.mean() / downside_returns.std() * np.sqrt(252)
        metriche_risultati['Ratio Sortino'] = round(sortino_ratio, 2)
    else:
        metriche_risultati['Ratio Sortino'] = float('inf') # O 0.0, a seconda di come vuoi rappresentare l'assenza di rischio negativo

    # Calmar Ratio
    annualized_return_from_equity_curve = (1 + daily_returns.mean())**252 - 1 if not daily_returns.empty else 0

    if max_drawdown_percent != 0:
        calmar_ratio = annualized_return_from_equity_curve / (max_drawdown_percent / 100)
        metriche_risultati['Ratio Calmar'] = round(calmar_ratio, 2)
    else:
        metriche_risultati['Ratio Calmar'] = float('inf')

    # Crea un nuovo dizionario con le metriche nello stesso ordine di 2_Testa_Strategie.py
    metriche_ordinate = {
        'Capitale Finale (€)': round(current_equity, 2),
        'Profitto/Perdita Totale (€)': round(total_pnl, 2),
        'Profitto/Perdita Totale (%)': round(total_pnl_percent, 2),
        'Rendimento Medio Annuale (%)': round(annualized_return, 2),
        'Numero Totale di Trade': total_trades,
        'Num. Trade Vincenti': num_winning_trades,
        'Num. Trade Perdenti': num_losing_trades,
        'Percentuale Trade Vincenti': round((num_winning_trades / total_trades * 100) if total_trades > 0 else 0, 2),
        'Num. Trade Long': num_long_trades,
        'P/L Medio Trade Long (%)': round(avg_long_pnl_percent, 2),
        'Num. Trade Short': num_short_trades,
        'P/L Medio Trade Short (%)': round(avg_short_pnl_percent, 2),
        'Profitto Medio Trade Vincenti (€)': round(avg_winning_trade, 2),
        'Profitto Medio Trade Vincenti (%)': round(avg_winning_trade_percent, 2),
        'Perdita Media Trade Perdenti (€)': round(avg_losing_trade, 2),
        'Perdita Media Trade Perdenti (%)': round(avg_losing_trade_percent, 2),
        'Profitto Massimo Trade (€)': round(max_profit, 2),
        'Profitto Massimo Trade (%)': round(max_profit_percent, 2),
        'Data Profitto Massimo': max_profit_date.strftime('%Y-%m-%d') if max_profit_date else 'N/A',
        'Perdita Massima Trade (€)': round(max_loss, 2),
        'Perdita Massima Trade (%)': round(max_loss_percent, 2),
        'Data Perdita Massima': max_loss_date.strftime('%Y-%m-%d') if max_loss_date else 'N/A',
        'Durata Media Trade (giorni)': round(avg_trade_duration, 1),
        'Max Drawdown (€)': round(max_drawdown_abs, 2),
        'Max Drawdown (%)': round(max_drawdown_percent, 2),
        'Ratio Sharpe': round(sharpe_ratio, 2),
        'Ratio Sortino': round(sortino_ratio, 2),
        'Ratio Calmar': round(calmar_ratio, 2)
    }
    
    # Aggiorna il dizionario delle metriche con l'ordine corretto
    metriche_risultati.clear()
    metriche_risultati.update(metriche_ordinate)

    return trade_log, equity_curve, buy_hold_equity_series, metriche_risultati
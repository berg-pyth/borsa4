# Note sui Calcoli - BorsaNew App


## Dati di ingresso e uscita
**Operazioni normali:** Acquisto/vendita al prezzo di chiusura del giorno del segnale
**Stop Loss/Take Profit/Trailing Stop:** Esecuzione al prezzo esatto del trigger
- Stop Loss LONG: Vendita al prezzo di stop loss
- Take Profit LONG: Vendita al prezzo di take profit  
- Trailing Stop LONG: Vendita al prezzo di trailing stop
- Stop Loss SHORT: Copertura al prezzo di stop loss
- Take Profit SHORT: Copertura al prezzo di take profit
- Trailing Stop SHORT: Copertura al prezzo di trailing stop

## Calcoli Principali

### Rendimento Medio Annuale
**Formula:** `(P/L Totale / Capitale Iniziale) × (365 / Giorni Totali) × 100`
- i Goirni totali sono i giorni di calendario dalla data della prima operazione di ingresso all'ultima data del periodo

**Esempio:**
- Capitale iniziale: €10,000
- P/L totale: €671.53
- Giorni totali: 1200 (dal 2022-03-15 al 2025-06-27)
- Calcolo: (671.53 / 10,000) × (365 / 1200) × 100 = 2.04% annuo

**Note:**
- Usa 365 giorni (calendario) invece di 252 (trading) perché `total_days` rappresenta giorni di calendario effettivi
- I primi ~50 giorni vengono rimossi per il calcolo degli indicatori (SMA 50)

### Calcolo P/L per Posizioni LONG
**Formula corretta:** `P/L = Ricavo netto - Costo originale lordo`

Dove:
- Ricavo netto = Quantità × Prezzo uscita × (1 - commissione%)
- Costo originale lordo = Quantità × Prezzo entrata × (1 + commissione%)
- quindi il calcolo P/L detrae già le spese di commissione e quindi le performance sono "nette"

**Esempio:**
- Acquisto: 100 azioni a €50 con commissione 0.2%
- Costo lordo = 100 × 50 × 1.002 = €5,010
- Vendita: 100 azioni a €55 con commissione 0.2%  
- Ricavo netto = 100 × 55 × 0.998 = €5,489
- P/L = €5,489 - €5,010 = €479

### Giorni Totali vs Giorni di Trading
**Giorni Totali:** Differenza calendario tra prima e ultima data dei dati
**Giorni di Trading:** Numero effettivo di record nel DataFrame

**Esempio periodo 2022-03-15 → 2025-06-27:**
- Giorni calendario teorici: 1,274
- Giorni calendario effettivi: 1,200 (nel calcolo)
- Giorni di trading: 825 (record DataFrame)

### Commissioni
**Applicazione:** Su ogni operazione (acquisto E vendita)
**Calcolo:** Percentuale sul valore nominale dell'operazione
**Default:** 0.2% per operazione

### Trailing Stop
**Concetto:** Stop loss dinamico che segue il prezzo nella direzione favorevole

**Per posizioni LONG:**
1. **Inizializzazione:** `trailing_stop_highest_price = current_high` (prezzo massimo del giorno di entrata)
2. **Aggiornamento:** Se `current_high > trailing_stop_highest_price`, aggiorna il massimo
3. **Calcolo stop:** `trailing_stop = trailing_stop_highest_price × (1 - trailing_stop_percent / 100)` (calcolato SEMPRE)
4. **Trigger con logica temporale:**
   - Se `current_close > current_open`: Massimo raggiunto DOPO minimo → NO trigger
   - Se `current_close ≤ current_open`: Massimo raggiunto PRIMA del minimo → trigger se `current_low ≤ trailing_stop`

**Per posizioni SHORT:**
1. **Inizializzazione:** `trailing_stop_lowest_price = current_low` (prezzo minimo del giorno di entrata)
2. **Aggiornamento:** Se `current_low < trailing_stop_lowest_price`, aggiorna il minimo
3. **Calcolo stop:** `trailing_stop = trailing_stop_lowest_price × (1 + trailing_stop_percent / 100)`
4. **Trigger con logica temporale:**
   - Se `current_close < current_open`: Minimo raggiunto DOPO massimo → NO trigger
   - Se `current_close ≥ current_open`: Minimo raggiunto PRIMA del massimo → trigger se `current_high ≥ trailing_stop`

**Esempio LONG con trailing stop 2%:**
- Entrata: €100
- Massimo raggiunto: €110 → trailing stop = €110 × 0.98 = €107.80
- Massimo raggiunto: €115 → trailing stop = €115 × 0.98 = €112.70
- Se prezzo scende a €112.70 → VENDITA automatica

**Priorità:** Trailing stop ha precedenza su stop loss fisso se entrambi attivi

- Nota che le percentuali (di perdita) degli stop (SL, SP, TS)  sono al netto delle spese di commissione.


## Indicatori Tecnici

### Medie Mobili (SMA)
- SMA 10: Rimuove primi 10 giorni (NaN)
- SMA 50: Rimuove primi 50 giorni (NaN)
- **Risultato:** I primi 50 giorni vengono eliminati dal backtest

### Supertrend
**Parametri:**
- Periodo ATR: default 10
- Moltiplicatore: default 3.0
- **Fix NumPy:** Aggiunto `np.NaN = np.nan` per compatibilità NumPy 2.0+

## Metriche di Performance

### Sharpe Ratio
**Formula:** `(Rendimento medio / Deviazione standard) × √252`
**Note:** Usa 252 giorni di trading per l'annualizzazione

### Max Drawdown
**Calcolo:** Massima perdita dal picco precedente
**Espresso in:** Valore assoluto (€) e percentuale (%)

### Profit Factor
**Formula:** `Profitti lordi / Perdite lorde`
**Interpretazione:** >1 = strategia profittevole

## Problemi Risolti

### NumPy 2.0+ Compatibility
**Problema:** `cannot import name 'NaN' from 'numpy'`
**Soluzione:** Aggiunto fix in tutti i file che importano pandas_ta:
```python
import numpy as np
if not hasattr(np, 'NaN'):
    np.NaN = np.nan
```

### SettingWithCopyWarning
**Problema:** Modifica di slice DataFrame
**Soluzione:** Sostituito loop con operazioni vettoriali usando `.loc`

## Versioni Software
- Python: 3.12.10 (specificato in runtime.txt)
- NumPy: <2.0.0 (per compatibilità)
- pandas-ta: 0.3.14b0 (versione fissa)

---
*Ultimo aggiornamento: Dicembre 2024*
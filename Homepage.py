#Homepage
# Fix NumPy 2.0+ compatibility
import numpy as np
if not hasattr(np, 'NaN'):
    np.NaN = np.nan

import streamlit as st

st.set_page_config(
    page_title="BorsaNew_app - Home",
    layout="wide",
    page_icon="📈"
)

# PWA Meta tags
st.markdown("""
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#ff6b6b">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="BorsaNew">
<link rel="apple-touch-icon" href="/static/icon-192.png">
""", unsafe_allow_html=True)

st.title("Benvenuto nella BorsaNew_app")
st.write("Questa piattaforma ti permette di scaricare i dati e vedere indicatori.")

# Disclaimer importante
st.error("⚠️ DISCLAIMER IMPORTANTE")
st.markdown("""
**Questo programma è puramente un esempio dimostrativo e non è stato testato per uso reale.**

- **NON utilizzare per strategie di trading reali**  
- **NON investire denaro basandosi su questi risultati**  
- **NON considerare come consulenza finanziaria**

L'autore non si assume alcuna responsabilità per eventuali perdite finanziarie.
""")

st.markdown("""
Utilizza il menu a sinistra  
""")
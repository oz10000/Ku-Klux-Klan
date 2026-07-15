"""
Archivo: streamlit_app.py
Proyecto: Krishna Omega Ultra — Dashboard Streamlit Final
Descripción: Interfaz profesional negro/verde. Robusta, tolerante a datos vacíos.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from src.config import LEVERAGE
from dashboard.data_loader import load_all
from dashboard.metrics_view import show_metrics
from dashboard.trades_view import show_trades
from dashboard.positions_view import show_positions
from dashboard.risk_view import show_risk
from dashboard.trailing_view import show_trailing

st.set_page_config(page_title="Krishna Omega Ultra", page_icon="🐺", layout="wide")

# Estilo terminal
st.markdown("""
<style>
    .main { background-color: #0a0a0a; }
    .stApp { background-color: #0a0a0a; }
    h1, h2, h3, p, div, label, span { color: #00ff00 !important; font-family: 'Courier New', monospace; }
    .stDataFrame { background-color: #111 !important; color: #00ff00 !important; }
    .stTab { color: #00ff00 !important; }
    .css-1d391kg { background-color: #0a0a0a; }
    .stMetric { color: #00ff00 !important; background-color: #111; padding: 10px; border-radius: 5px; }
    .stTextArea textarea { background-color: #000; color: #00ff00; font-family: 'Courier New', monospace; }
    button { background-color: #111 !important; color: #00ff00 !important; border: 1px solid #00ff00 !important; }
    hr { border-color: #333; }
</style>
""", unsafe_allow_html=True)

st.title("🐺 KRISHNA OMEGA ULTRA — Terminal Dashboard")

# Cargar datos con valores por defecto robustos
data = load_all()
metrics = data.get('metrics') or {}
trades = data.get('trades') or []
positions = data.get('positions') or []
margin_factors = data.get('margin_factors') or {}
logs_text = data.get('logs') or ''

# Refresco manual
if st.button("🔄 REFRESCAR DATOS"):
    st.rerun()

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 DASHBOARD", "💰 TRADES", "📈 MÉTRICAS", "🔍 POSICIONES",
    "🎯 TRAILING", "⚠️ RIESGO", "📋 LOGS"
])

# ───────────────────── TAB 1 ─────────────────────
with tab1:
    st.header("ESTADO DEL SISTEMA")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Balance", f"{metrics.get('final_equity', 0):.2f} USDT")
    with col2:
        st.metric("PnL Total", f"{metrics.get('net_pnl', 0):.2f} USDT")
    with col3:
        st.metric("Posiciones", len([p for p in positions if not p.get('closed', False)]))
    with col4:
        st.metric("Trades", len(trades))

    st.markdown("---")
    st.subheader("RENDIMIENTO EN TIEMPO REAL")
    col1, col2, col3, col4 = st.columns(4)

    # Calcular métricas horarias/diarias de forma segura
    try:
        start_str = data.get('start_time')
        if start_str:
            start_dt = datetime.fromisoformat(start_str)
            hours = max((datetime.now() - start_dt).total_seconds() / 3600, 1)
            days = max((datetime.now() - start_dt).days, 1)
            pnl_hour = metrics.get('net_pnl', 0) / hours
            pnl_day = metrics.get('net_pnl', 0) / days
            trades_hour = len(trades) / hours
            trades_day = len(trades) / days
        else:
            pnl_hour = pnl_day = trades_hour = trades_day = 0.0
    except Exception:
        pnl_hour = pnl_day = trades_hour = trades_day = 0.0

    with col1:
        st.metric("PnL / hora", f"{pnl_hour:.2f} USDT")
    with col2:
        st.metric("PnL / día", f"{pnl_day:.2f} USDT")
    with col3:
        st.metric("Trades / hora", f"{trades_hour:.2f}")
    with col4:
        st.metric("Win Rate", f"{metrics.get('win_rate', 0):.1f}%")

# ───────────────────── TAB 2 ─────────────────────
with tab2:
    show_trades(trades)

# ───────────────────── TAB 3 ─────────────────────
with tab3:
    show_metrics(metrics)

# ───────────────────── TAB 4 ─────────────────────
with tab4:
    show_positions(positions)

# ───────────────────── TAB 5 ─────────────────────
with tab5:
    show_trailing()

# ───────────────────── TAB 6 ─────────────────────
with tab6:
    show_risk(metrics, margin_factors)

# ───────────────────── TAB 7 ─────────────────────
with tab7:
    st.header("LOGS DEL SISTEMA")
    st.text_area("Salida de consola", logs_text, height=500)

# Auto‑refresco cada 10 segundos
st.markdown("""
<script>
setTimeout(function(){ window.location.reload(); }, 10000);
</script>
""", unsafe_allow_html=True)

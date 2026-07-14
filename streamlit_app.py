"""
Archivo: streamlit_app.py
Proyecto: Krishna Omega Ultra — Dashboard Streamlit Final
Descripción: Interfaz profesional negro/verde con 7 pestañas,
datos persistentes reales y refresh automático.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from src.config import LEVERAGE
from src.state_manager import StateManager
from dashboard.data_loader import load_all
from dashboard.metrics_view import show_metrics
from dashboard.trades_view import show_trades
from dashboard.positions_view import show_positions
from dashboard.risk_view import show_risk
from dashboard.trailing_view import show_trailing

st.set_page_config(page_title="Krishna Omega Ultra", page_icon="🐺", layout="wide")

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

# Carga inicial de datos
data = load_all()
metrics = data.get('metrics', {})

# Botón de refresco manual
if st.button("🔄 REFRESCAR DATOS"):
    st.rerun()

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 DASHBOARD", "💰 TRADES", "📈 MÉTRICAS", "🔍 POSICIONES",
    "🎯 TRAILING", "⚠️ RIESGO", "📋 LOGS"
])

with tab1:
    st.header("ESTADO DEL SISTEMA")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Balance", f"{metrics.get('final_equity', 0):.2f} USDT")
    with col2:
        st.metric("PnL Total", f"{metrics.get('net_pnl', 0):.2f} USDT")
    with col3:
        st.metric("Posiciones", len(data.get('positions', [])))
    with col4:
        st.metric("Trades", len(data.get('trades', [])))

    st.markdown("---")
    st.subheader("RENDIMIENTO EN TIEMPO REAL")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pnl_hour = metrics.get('net_pnl', 0) / max((datetime.now() - datetime.strptime(data.get('start_time', datetime.now().isoformat()), '%Y-%m-%dT%H:%M:%S')).total_seconds() / 3600, 1)
        st.metric("PnL / hora", f"{pnl_hour:.2f} USDT")
    with col2:
        st.metric("PnL / día", f"{metrics.get('net_pnl', 0) / max((datetime.now() - datetime.strptime(data.get('start_time', datetime.now().isoformat()), '%Y-%m-%dT%H:%M:%S')).days, 1):.2f} USDT" if metrics.get('net_pnl') else "0.00 USDT")
    with col3:
        trades_hour = len(data.get('trades', [])) / max((datetime.now() - datetime.strptime(data.get('start_time', datetime.now().isoformat()), '%Y-%m-%dT%H:%M:%S')).total_seconds() / 3600, 1)
        st.metric("Trades / hora", f"{trades_hour:.2f}")
    with col4:
        st.metric("Win Rate", f"{metrics.get('win_rate', 0):.1f}%")

with tab2:
    show_trades(data.get('trades', []))

with tab3:
    show_metrics(metrics)

with tab4:
    show_positions(data.get('positions', []))

with tab5:
    show_trailing()

with tab6:
    show_risk(metrics, data.get('margin_factors', {}))

with tab7:
    st.header("LOGS DEL SISTEMA")
    st.text_area("Salida de consola", data.get('logs', ''), height=500)

# Auto-refresh cada 10 segundos
st.markdown("""
<script>
setTimeout(function(){ window.location.reload(); }, 10000);
</script>
""", unsafe_allow_html=True)

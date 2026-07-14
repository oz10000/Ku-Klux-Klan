"""
Archivo: dashboard/metrics_view.py
Proyecto: Krishna Omega Ultra
Descripción: Visualización de métricas en Streamlit.
"""
import streamlit as st

def show_metrics(metrics):
    if not metrics:
        st.info("No hay métricas disponibles")
        return
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Profit Factor", metrics.get('profit_factor', 0))
        st.metric("Sharpe Ratio", metrics.get('sharpe_ratio', 0))
        st.metric("Sortino Ratio", metrics.get('sortino_ratio', 0))
        st.metric("Calmar Ratio", metrics.get('calmar_ratio', 0))
    with col2:
        st.metric("Max Drawdown", f"{metrics.get('max_drawdown_pct', 0)}%")
        st.metric("Expectancy", f"{metrics.get('expectancy', 0):.2f} USDT")
        st.metric("Avg Win", f"{metrics.get('avg_win', 0):.2f} USDT")
        st.metric("Avg Loss", f"{metrics.get('avg_loss', 0):.2f} USDT")

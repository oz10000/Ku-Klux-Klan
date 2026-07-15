"""
Archivo: dashboard/risk_view.py
Proyecto: Krishna Omega Ultra
Descripción: Panel de riesgo en Streamlit.
"""
import streamlit as st
from src.config import LEVERAGE

def show_risk(metrics, margin_factors):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Apalancamiento", f"{LEVERAGE}x")
    with col2:
        st.metric("Drawdown", f"{metrics.get('max_drawdown_pct', 0)}%")
    with col3:
        kill = "ACTIVO" if metrics.get('max_drawdown_pct', 0) >= 12 else "INACTIVO"
        st.metric("Kill Switch", kill)
    st.subheader("Factores de margen")
    if margin_factors:
        try:
            st.json(margin_factors)
        except:
            st.info("Sin datos")
    else:
        st.info("Sin datos")

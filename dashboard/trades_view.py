"""
Archivo: dashboard/trades_view.py
Proyecto: Krishna Omega Ultra
Descripción: Tabla de trades en Streamlit.
"""
import streamlit as st
import pandas as pd

def show_trades(trades):
    if trades:
        try:
            df = pd.DataFrame(trades)
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error al mostrar trades: {e}")
    else:
        st.info("No hay trades registrados")

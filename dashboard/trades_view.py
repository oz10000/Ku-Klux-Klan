"""
Archivo: dashboard/trades_view.py
Proyecto: Krishna Omega Ultra
Descripción: Tabla de trades en Streamlit.
"""
import streamlit as st
import pandas as pd

def show_trades(trades):
    if trades:
        df = pd.DataFrame(trades)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay trades registrados")

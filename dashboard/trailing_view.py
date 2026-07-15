"""
Archivo: dashboard/trailing_view.py
Proyecto: Krishna Omega Ultra
Descripción: Visualización del trailing engine en Streamlit.
"""
import streamlit as st
import json, os

def show_trailing():
    st.info("Estado del trailing engine (requiere bot activo)")
    path = "state/trailing_events.json"
    if os.path.exists(path):
        try:
            with open(path) as f:
                events = json.load(f)
            if events:
                import pandas as pd
                st.dataframe(pd.DataFrame(events), use_container_width=True)
            else:
                st.info("Sin eventos")
        except Exception as e:
            st.error(f"Error al leer trailing events: {e}")
    else:
        st.info("No se encontró historial de trailing")

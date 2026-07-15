"""
Archivo: dashboard/positions_view.py
Proyecto: Krishna Omega Ultra
Descripción: Posiciones abiertas en Streamlit.
"""
import streamlit as st

def show_positions(positions):
    try:
        active = [p for p in positions if not p.get('closed', False)]
    except:
        active = []
    if not active:
        st.info("Sin posiciones abiertas")
        return
    for p in active:
        st.markdown(f"**📍 {p['symbol']} | {p['side']}**")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"Entrada: {p['entry']}")
            st.write(f"TP: {p.get('tp', 'N/A')}")
        with col2:
            st.write(f"Tamaño: {p['size']}")
            st.write(f"SL: {p.get('sl', 'N/A')}")
        st.markdown("---")

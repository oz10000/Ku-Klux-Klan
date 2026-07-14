"""
Archivo: dashboard/data_loader.py
Proyecto: Krishna Omega Ultra
Descripción: Carga de datos persistentes desde StateManager.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.state_manager import StateManager

def load_all():
    sm = StateManager()
    return sm.load_all()

# regime_detector.py
# Krishna Omega Ultra V9.1.1 — Detector de regímenes de mercado

import numpy as np
import pandas as pd
from src.indicators import atr, adx, ker

REGIME_TYPES = [
    'Tendencia Fuerte',
    'Tendencia Débil',
    'Normal',
    'Compresión',
    'Expansión',
    'Alta Volatilidad',
    'Chop (Lateral)',
    'Indefinido'
]

def classify_regime(df):
    """
    Clasifica el régimen de mercado actual.
    Retorna: (regime_name, confidence, metrics)
    """
    if len(df) < 60:
        return ('Indefinido', 0.0, {})
    
    close = df['close']
    atr_val = atr(df, 12).iloc[-1]
    adx_val = adx(df, 24).iloc[-1]
    ker_val = ker(close, 10).iloc[-1]
    atr_pct = atr_val / close.iloc[-1] * 100
    volatility = close.pct_change().std() * 100
    
    metrics = {
        'adx': adx_val,
        'ker': ker_val,
        'atr_pct': atr_pct,
        'volatility': volatility,
        'trend_strength': adx_val / 40.0,
        'efficiency': ker_val
    }
    
    # Alta volatilidad
    if atr_pct > 3.5 or volatility > 3.0:
        return ('Alta Volatilidad', 0.85, metrics)
    
    # Tendencia fuerte
    if adx_val > 28 and ker_val > 0.6:
        return ('Tendencia Fuerte', 0.90, metrics)
    
    # Tendencia débil
    if adx_val > 22 and ker_val > 0.5:
        return ('Tendencia Débil', 0.75, metrics)
    
    # Chop (lateral)
    if ker_val < 0.4 or adx_val < 20:
        return ('Chop (Lateral)', 0.80, metrics)
    
    # Compresión
    if atr_pct < 1.0 and adx_val < 25 and ker_val < 0.5:
        return ('Compresión', 0.70, metrics)
    
    # Expansión
    if atr_pct > 2.0 and adx_val > 25:
        return ('Expansión', 0.75, metrics)
    
    return ('Normal', 0.60, metrics)

def get_regime_params(regime):
    """
    Retorna parámetros óptimos para cada régimen.
    """
    params = {
        'Tendencia Fuerte': {
            'tp_mult': 3.0, 'sl_mult': 1.0, 'trail_mult': 1.3,
            'be_activation': 0.3, 'max_duration': 90, 'leverage': 3,
            'min_score': 0.35
        },
        'Tendencia Débil': {
            'tp_mult': 2.5, 'sl_mult': 1.2, 'trail_mult': 1.5,
            'be_activation': 0.5, 'max_duration': 75, 'leverage': 2,
            'min_score': 0.40
        },
        'Normal': {
            'tp_mult': 2.0, 'sl_mult': 1.2, 'trail_mult': 1.5,
            'be_activation': 0.5, 'max_duration': 60, 'leverage': 2,
            'min_score': 0.45
        },
        'Compresión': {
            'tp_mult': 2.0, 'sl_mult': 1.0, 'trail_mult': 1.2,
            'be_activation': 0.4, 'max_duration': 45, 'leverage': 2,
            'min_score': 0.50
        },
        'Expansión': {
            'tp_mult': 3.5, 'sl_mult': 1.5, 'trail_mult': 2.0,
            'be_activation': 0.7, 'max_duration': 60, 'leverage': 2,
            'min_score': 0.35
        },
        'Alta Volatilidad': {
            'tp_mult': 4.0, 'sl_mult': 2.0, 'trail_mult': 2.5,
            'be_activation': 1.0, 'max_duration': 45, 'leverage': 1,
            'min_score': 0.50
        },
        'Chop (Lateral)': {
            'tp_mult': 1.5, 'sl_mult': 0.8, 'trail_mult': 1.0,
            'be_activation': 0.3, 'max_duration': 30, 'leverage': 1,
            'min_score': 0.60,
            'no_trade': True
        }
    }
    return params.get(regime, params['Normal'])

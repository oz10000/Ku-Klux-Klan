"""
Archivo: src/opportunity_ranker.py
Proyecto: Krishna Omega Ultra V9.1
Descripción: Opportunity Score con penalización por extensión VWAP.
"""
import numpy as np
from src.indicators import atr, adx, ker, vwap_zscore
from src.config import *

def calculate_opportunity_score(signal: dict, data_5m: dict) -> float:
    sym = signal['symbol']
    df = data_5m.get(sym)
    if df is None or len(df) < 20: return 0.0

    adx_val = float(adx(df, 14).iloc[-1])
    ker_val = float(ker(df['c'], 10).iloc[-1])
    vel = abs(df['c'].iloc[-1] / df['c'].iloc[-4] - 1) * 100 if len(df) >= 4 else 0.0
    atr_now = float(atr(df, 12).iloc[-1])
    atr_ma = float(atr(df, 12).rolling(50).mean().iloc[-1]) if len(df) >= 50 else atr_now
    atr_exp = min(atr_now / atr_ma, 2.0) if atr_ma > 0 else 1.0
    vol_now = float(df['vol'].iloc[-1])
    vol_ma = float(df['vol'].rolling(50).mean().iloc[-1]) if len(df) >= 50 else vol_now
    vol_rel = min(vol_now / vol_ma, 2.0) if vol_ma > 0 else 1.0
    vwz = float(vwap_zscore(df, VWAP_PERIOD).iloc[-1])

    adx_norm = min(adx_val / 40.0, 1.0)
    ker_norm = ker_val
    vel_norm = min(vel / 5.0, 1.0)
    atr_norm = max(0.0, (atr_exp - 1.0) / 1.0)
    vol_norm = max(0.0, (vol_rel - 1.0) / 1.0)

    base = (adx_norm * 0.25 + ker_norm * 0.25 + vel_norm * 0.20 +
            atr_norm * 0.15 + vol_norm * 0.15)

    if EXTENSION_PENALTY_ENABLED and abs(vwz) > VWAP_EXTENSION_THRESHOLD:
        base *= EXTENSION_PENALTY_FACTOR

    return float(base)

def rank_signals(signals: list, data_5m: dict) -> list:
    scored = [(calculate_opportunity_score(s, data_5m), s) for s in signals]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored]

"""
Archivo: src/strategy_rama_b.py
Proyecto: Krishna Omega Ultra
Descripción: Estrategia con scoring horario corregido (sin solapamiento),
SL_MULT definido y volumen real en time_score.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from src.indicators import *
from src.config import *

def compute_time_score(hour_utc: int, adx_val: float, atr_pct: float, volume_ratio: float = 1.0) -> float:
    """
    Calcula un score de 0-100 basado en la sesión horaria y condiciones técnicas.
    Sin solapamiento entre sesiones.
    """
    score = 0.0
    if 8 <= hour_utc < 14:          # Sesión europea (mañana)
        score += 30
    elif 14 <= hour_utc <= 22:      # Sesión americana (tarde)
        score += 25
    else:                            # Sesión asiática / baja liquidez
        score += 10

    if adx_val > 25:
        score += 20
    if atr_pct > 1.5:
        score += 15
    if volume_ratio > 1.2:
        score += 15
    return min(100, score)


class StrategyRamaB:
    def __init__(self, exchange):
        self.exchange = exchange

    def generate_signal(self, data5, data15):
        best = None
        best_rank = -1e9
        now_utc = datetime.utcnow()

        for sym in UNIVERSO:
            if sym not in data5 or sym not in data15:
                continue
            df5 = data5[sym]
            if len(df5) < 60:
                continue

            sc = compute_score(df5)
            if abs(sc) < MIN_SCORE:
                continue

            adx_val = adx(df5, ADX_THRESHOLD).iloc[-1]
            ker_val = ker(df5['c'], KER_PERIOD).iloc[-1]
            if adx_val < ADX_THRESHOLD or ker_val < KER_THRESHOLD:
                continue

            regime = classify_regime(df5)
            if regime in ['Chop', 'Compresión']:
                continue

            df15_sym = data15[sym]
            if len(df15_sym) < 20:
                continue
            ema15 = df15_sym['c'].ewm(span=20, adjust=False).mean().iloc[-1]
            direction = 'Long' if sc > 0 else 'Short'
            if (direction == 'Long' and df5.iloc[-1]['c'] < ema15) or \
               (direction == 'Short' and df5.iloc[-1]['c'] > ema15):
                continue

            # Scoring horario con volumen real
            if TIME_SCORE_ENABLED:
                atr_pct_val = atr(df5, ATR_PERIOD).iloc[-1] / df5.iloc[-1]['c'] * 100
                # Volumen relativo real (último vs media móvil 20)
                vol_ratio = 1.0
                if 'vol' in df5.columns and len(df5) >= 20:
                    avg_vol = df5['vol'].rolling(20).mean().iloc[-1]
                    if avg_vol > 0:
                        vol_ratio = df5['vol'].iloc[-1] / avg_vol
                ts = compute_time_score(now_utc.hour, adx_val, atr_pct_val, vol_ratio)
                if ts < TIME_SCORE_THRESHOLD and abs(sc) < TIME_SCORE_MIN_FOR_ENTRY:
                    continue

            atr_val = atr(df5, ATR_PERIOD).iloc[-1]
            mac_val = macro(df5, MACRO_LOOKBACK).iloc[-1]
            mom_val = df5['c'].pct_change(MOMENTUM_PERIOD).iloc[-1] * 100
            vwz = abs(vwap_zscore(df5, VWAP_PERIOD).iloc[-1]) / 3.0
            atr_rel = min(1.0, atr_val / df5.iloc[-1]['c'] * 100 / 3.5)
            adx_n = min(1.0, adx_val / 40.0)
            mom_n = min(1.0, abs(mom_val) / 5.0)

            rank = (abs(sc) * 0.25 + adx_n * 0.20 + ker_val * 0.15 +
                    mac_val * 0.10 + atr_rel * 0.10 + vwz * 0.10 + mom_n * 0.10)

            if rank > best_rank:
                best_rank = rank
                entry = df5.iloc[-1]['c']
                tp = entry + atr_val * TP_MULT_INIT if direction == 'Long' else entry - atr_val * TP_MULT_INIT
                sl = entry - atr_val * SL_MULT if direction == 'Long' else entry + atr_val * SL_MULT
                best = {
                    'symbol': sym,
                    'direction': direction,
                    'entry': entry,
                    'tp': tp,
                    'sl': sl,
                    'score': sc,
                    'time_score': ts if TIME_SCORE_ENABLED else 100,
                    'volume_ratio': vol_ratio
                }
        return best

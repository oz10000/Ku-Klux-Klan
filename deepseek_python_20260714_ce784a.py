"""
Archivo: src/strategy_rama_b.py
Proyecto: Krishna Omega Ultra
Descripción: Estrategia Rama B (5m + confirmación 15m). Selecciona la mejor señal usando scoring compuesto y filtros.
"""
import pandas as pd
import numpy as np
from src.indicators import *
from src.config import *

class StrategyRamaB:
    def __init__(self, exchange):
        self.exchange = exchange

    def generate_signal(self, data5, data15):
        best = None; best_rank = -1e9
        for sym in UNIVERSO:
            if sym not in data5 or sym not in data15: continue
            df5 = data5[sym]
            if len(df5)<60: continue
            sc = compute_score(df5)
            if abs(sc)<MIN_SCORE: continue
            adx_val = adx(df5, ADX_THRESHOLD).iloc[-1]
            ker_val = ker(df5['c'], KER_PERIOD).iloc[-1]
            if adx_val<ADX_THRESHOLD or ker_val<KER_THRESHOLD: continue
            regime = classify_regime(df5)
            if regime in ['Chop','Compresión']: continue
            df15 = data15[sym]
            if len(df15)<20: continue
            ema15 = df15['c'].ewm(span=20, adjust=False).mean().iloc[-1]
            dir = 'Long' if sc>0 else 'Short'
            if (dir=='Long' and df5.iloc[-1]['c']<ema15) or (dir=='Short' and df5.iloc[-1]['c']>ema15): continue
            atr_val = atr(df5, ATR_PERIOD).iloc[-1]
            mac_val = macro(df5, MACRO_LOOKBACK).iloc[-1]
            mom_val = df5['c'].pct_change(MOMENTUM_PERIOD).iloc[-1]*100
            vwz = abs(vwap_zscore(df5, VWAP_PERIOD).iloc[-1])/3.0
            atr_rel = min(1.0, atr_val/df5.iloc[-1]['c']*100/3.5)
            adx_n = min(1.0, adx_val/40.0)
            mom_n = min(1.0, abs(mom_val)/5.0)
            rank = (abs(sc)*0.25 + adx_n*0.20 + ker_val*0.15 + mac_val*0.10 +
                    atr_rel*0.10 + vwz*0.10 + mom_n*0.10)
            if rank>best_rank:
                best_rank = rank; entry = df5.iloc[-1]['c']
                tp = entry + atr_val*TP_MULT_INIT if dir=='Long' else entry - atr_val*TP_MULT_INIT
                sl = entry - atr_val*SL_MULT if dir=='Long' else entry + atr_val*SL_MULT
                best = {'symbol':sym,'direction':dir,'entry':entry,'tp':tp,'sl':sl,'score':sc}
        return best
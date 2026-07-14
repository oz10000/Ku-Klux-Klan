"""
Archivo: src/indicators.py
Proyecto: Krishna Omega Ultra
Descripción: Cálculo de indicadores técnicos y clasificación de régimen.
"""
import numpy as np
import pandas as pd
from src.config import *

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def atr(df, period):
    tr = pd.concat([df['h'] - df['l'],
                    abs(df['h'] - df['c'].shift()),
                    abs(df['l'] - df['c'].shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def adx(df, period):
    a = atr(df, period)
    up_move = df['h'].diff()
    down_move = -df['l'].diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0).rolling(period).mean()
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0).rolling(period).mean()
    plus_di = 100 * plus_dm / (a + 1e-9)
    minus_di = 100 * minus_dm / (a + 1e-9)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
    return dx.rolling(period).mean()

def ker(close, period):
    abs_diff = abs(close.diff(period))
    sum_abs = close.diff().abs().rolling(period).sum()
    ker_val = abs_diff / (sum_abs + 1e-9)
    return ker_val.fillna(0)

def vwap_zscore(df, period):
    vwap = (df['c'] * df['vol']).rolling(period).sum() / (df['vol'].rolling(period).sum() + 1e-9)
    std = df['c'].rolling(period).std()
    return (df['c'] - vwap) / (std + 1e-9)

def macro(df, period):
    a = atr(df, ATR_PERIOD)
    macro_val = a.rolling(period).apply(
        lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min() + 1e-9)
    )
    return macro_val.clip(0, 1)

def classify_regime(df):
    if len(df) < 60:
        return 'Indefinido'
    c = df.iloc[-60:]
    adx_val = adx(c, ADX_THRESHOLD).iloc[-1]
    ker_val = ker(c['c'], KER_PERIOD).iloc[-1]
    atr_pct = atr(c, ATR_PERIOD).iloc[-1] / c.iloc[-1]['c'] * 100
    if adx_val > 28 and ker_val > 0.6:
        return 'Tendencia Fuerte'
    if ker_val < 0.45 or adx_val < 20:
        return 'Chop'
    if atr_pct < 1.0 and adx_val < 25:
        return 'Compresión'
    return 'Normal'

def compute_score(df):
    if len(df) < 50:
        return 0.0
    k = ker(df['c'], KER_PERIOD)
    v = vwap_zscore(df, VWAP_PERIOD)
    a = atr(df, ATR_PERIOD)
    e = ema(df['c'], EMA_FAST)
    slope = (df['c'] - e) / (a + 1e-9)
    adx_vals = adx(df, ADX_THRESHOLD)
    mom = df['c'].pct_change(MOMENTUM_PERIOD) * 100
    mac = macro(df, MACRO_LOOKBACK)

    last_k = k.iloc[-1]
    last_v = v.iloc[-1]
    last_slope = slope.iloc[-1]
    last_adx = adx_vals.iloc[-1]
    last_mom = mom.iloc[-1]
    last_mac = mac.iloc[-1]

    trend = np.tanh(last_slope)
    strength = min(1.0, last_adx / 40.0)
    atr_rel_norm = min(1.0, a.iloc[-1] / df['c'].iloc[-1] * 100 / 3.5)
    mom_norm = min(1.0, abs(last_mom) / 5.0)

    raw = (PIDELTA_WEIGHTS['velocity_momentum'] * trend +
           PIDELTA_WEIGHTS['adx'] * strength +
           PIDELTA_WEIGHTS['ker'] * last_k +
           PIDELTA_WEIGHTS['macro'] * last_mac +
           PIDELTA_WEIGHTS['atr_rel'] * atr_rel_norm +
           PIDELTA_WEIGHTS['vwap_z'] * last_v +
           PIDELTA_WEIGHTS['momentum'] * mom_norm)
    return float(np.tanh(raw))

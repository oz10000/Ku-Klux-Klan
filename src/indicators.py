# indicators.py
# Krishna Omega Ultra V9.1.1 — Indicadores técnicos (incluye RSI y MACD)

import numpy as np
import pandas as pd

# ---------- INDICADORES EXISTENTES ----------
def atr(df, period=12):
    if len(df) < period + 1:
        return pd.Series([0.0] * len(df), index=df.index)
    tr1 = df["high"] - df["low"]
    tr2 = abs(df["high"] - df["close"].shift())
    tr3 = abs(df["low"] - df["close"].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def adx(df, period=24):
    if len(df) < period + 1:
        return pd.Series([0.0] * len(df), index=df.index)
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = low.diff()
    plus_dm = pd.Series(0.0, index=df.index)
    minus_dm = pd.Series(0.0, index=df.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move
    atr_val = atr(df, period)
    plus_di = 100 * plus_dm.rolling(period).mean() / atr_val
    minus_di = 100 * minus_dm.rolling(period).mean() / atr_val
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
    return dx.rolling(period).mean()

def ker(close, period=10):
    if len(close) < period + 1:
        return pd.Series([0.0] * len(close), index=close.index)
    abs_diff = abs(close.diff(period))
    sum_abs = close.diff().abs().rolling(period).sum()
    return (abs_diff / (sum_abs + 1e-9)).fillna(0)

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def vwap_zscore(df, period=20):
    if len(df) < period:
        return pd.Series([0.0] * len(df), index=df.index)
    vwap = (df["close"] * df["volume"]).rolling(period).sum() / (df["volume"].rolling(period).sum() + 1e-9)
    std = df["close"].rolling(period).std()
    return (df["close"] - vwap) / (std + 1e-9)

# ---------- NUEVOS INDICADORES ----------
def rsi(close, period=14):
    """Relative Strength Index"""
    if len(close) < period + 1:
        return pd.Series([50.0] * len(close), index=close.index)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def macd(close, fast=12, slow=26, signal=9):
    """MACD (Moving Average Convergence Divergence)"""
    if len(close) < slow + signal:
        return (
            pd.Series(0.0, index=close.index),
            pd.Series(0.0, index=close.index),
            pd.Series(0.0, index=close.index),
        )
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

# ---------- PiDelta Score ----------
def compute_score(df, weights=None):
    if len(df) < 50:
        return 0.0
    close = df["close"]
    atr_val = atr(df, 12)
    ema22 = ema(close, 22)
    trend = np.tanh((close - ema22) / (atr_val + 1e-9)).iloc[-1]
    adx_val = adx(df, 24).iloc[-1]
    strength = min(1.0, adx_val / 40.0)
    ker_val = ker(close, 10).iloc[-1]
    if len(df) >= 18:
        macro_atr = (
            atr(df, 12)
            .rolling(18)
            .apply(lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min() + 1e-9))
            .iloc[-1]
        )
    else:
        macro_atr = 0.5
    atr_rel = min(1.0, (atr_val.iloc[-1] / close.iloc[-1] * 100) / 3.5)
    vwap_z = vwap_zscore(df, 20).iloc[-1]
    mom = close.pct_change(5).iloc[-1] * 100
    mom_norm = min(1.0, abs(mom) / 5.0)

    if weights is None:
        from src.config import PIDELTA_WEIGHTS
        weights = PIDELTA_WEIGHTS

    raw = (
        weights["velocity_momentum"] * trend
        + weights["adx"] * strength
        + weights["ker"] * ker_val
        + weights["macro"] * macro_atr
        + weights["atr_rel"] * atr_rel
        + weights["vwap_z"] * vwap_z
        + weights["momentum"] * mom_norm
    )
    return float(np.tanh(raw))

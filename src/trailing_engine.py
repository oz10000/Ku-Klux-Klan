"""
Archivo: src/trailing_engine.py
Proyecto: Krishna Omega Ultra V9.1
Descripción: Motor de stops dinámicos multi‑timeframe.
Incluye Break Even, Trailing Stop, Trailing TP, Velocity Exit y timeout adaptativo.
"""
import numpy as np
from datetime import datetime
from src.indicators import *
from src.config import *
from src.logger import get_logger

logger = get_logger(__name__)

class TrailingEngine:
    def __init__(self, entry_price: float, entry_time: datetime, symbol: str, side: str):
        self.entry = entry_price
        self.side = side
        self.symbol = symbol
        self.entry_time = entry_time
        self.current_sl = None
        self.current_tp_trail_active = False
        self.current_tp_sl = None
        self.be_activated = False
        self.last_trail_distance = None

    def evaluate(self, candle_5m: dict, df_5m, df_1m, df_15m) -> dict:
        close = candle_5m['c']
        high = candle_5m['h']
        low = candle_5m['l']
        elapsed_min = (datetime.utcnow() - self.entry_time).total_seconds() / 60.0

        # ATRs
        atr_5 = self._safe_atr(df_5m, ATR_PERIOD)
        atr_1 = self._safe_atr(df_1m, ATR_PERIOD) if df_1m is not None and len(df_1m) > 20 else atr_5
        atr_15 = self._safe_atr(df_15m, ATR_PERIOD) if df_15m is not None and len(df_15m) > 20 else atr_5

        # ADX y KER
        adx_val = self._safe_adx(df_5m)
        ker_val = self._safe_ker(df_5m)

        # Cálculo dinámico del trailing stop
        base_mult = TRAIL_STOP_BASE_MULT
        if adx_val > 30:
            base_mult *= 0.7
        elif adx_val > 25:
            base_mult *= 0.85
        if ker_val > 0.6:
            base_mult *= 0.8
        if df_1m is not None and len(df_1m) > 3:
            roc_1m = (df_1m['c'].iloc[-1] / df_1m['c'].iloc[-4] - 1) * 100
            if abs(roc_1m) > 0.5:
                base_mult *= 0.9
        base_mult = max(TRAIL_STOP_MIN_MULT, min(TRAIL_STOP_MAX_MULT, base_mult))
        trail_distance = base_mult * atr_5
        min_price_distance = close * 0.003
        trail_distance = max(trail_distance, min_price_distance)
        self.last_trail_distance = trail_distance

        # Calcular nuevo SL
        if self.side == 'long':
            new_sl = close - trail_distance
            if self.current_sl is None or new_sl > self.current_sl:
                self.current_sl = new_sl
        else:
            new_sl = close + trail_distance
            if self.current_sl is None or new_sl < self.current_sl:
                self.current_sl = new_sl

        # Verificar SL
        if self.side == 'long' and low <= self.current_sl:
            return {'action': 'CLOSE', 'price': self.current_sl, 'reason': 'SL'}
        elif self.side == 'short' and high >= self.current_sl:
            return {'action': 'CLOSE', 'price': self.current_sl, 'reason': 'SL'}

        # ---------- Velocity Momentum Exit ----------
        if VELOCITY_EXIT_ENABLED and not self.be_activated and not self.current_tp_trail_active:
            profit_pct = (close - self.entry) / self.entry * 100 if self.side == 'long' else (self.entry - close) / self.entry * 100
            if profit_pct >= VELOCITY_EXIT_MIN_PROFIT_PCT and elapsed_min <= VELOCITY_EXIT_MAX_MINUTES:
                if adx_val >= VELOCITY_EXIT_MIN_ADX and ker_val >= VELOCITY_EXIT_MIN_KER:
                    return {'action': 'CLOSE', 'price': close, 'reason': 'VelocityExit'}

        # Trailing TP
        if not self.current_tp_trail_active:
            tp_activation_distance = TP_MULT_INIT * atr_5
            if (self.side == 'long' and close >= self.entry + tp_activation_distance) or \
               (self.side == 'short' and close <= self.entry - tp_activation_distance):
                self.current_tp_trail_active = True
                self.current_tp_sl = close - (TRAIL_TP_BASE_MULT * atr_5) if self.side == 'long' else close + (TRAIL_TP_BASE_MULT * atr_5)
                return {'action': 'ACTIVATE_TP_TRAIL', 'price': self.current_tp_sl}
        else:
            tp_mult = TRAIL_TP_BASE_MULT
            if adx_val < 25:
                tp_mult = max(TRAIL_TP_MIN_MULT, tp_mult * 0.8)
            tp_distance = tp_mult * atr_5
            if self.side == 'long':
                new_tp_sl = close - tp_distance
                if new_tp_sl > self.current_tp_sl:
                    self.current_tp_sl = new_tp_sl
                    return {'action': 'MOVE_SL', 'price': new_tp_sl}
            else:
                new_tp_sl = close + tp_distance
                if new_tp_sl < self.current_tp_sl:
                    self.current_tp_sl = new_tp_sl
                    return {'action': 'MOVE_SL', 'price': new_tp_sl}

        # Break Even
        if not self.be_activated and elapsed_min >= BREAK_EVEN_MINUTES:
            profit_pct = (close - self.entry) / self.entry * 100 if self.side == 'long' else (self.entry - close) / self.entry * 100
            if profit_pct >= BREAK_EVEN_ACTIVATION_PCT:
                self.be_activated = True
                be_sl = self.entry * (1 + BREAK_EVEN_BUFFER_PCT / 100.0) if self.side == 'long' else self.entry * (1 - BREAK_EVEN_BUFFER_PCT / 100.0)
                if self.current_sl is None or (self.side == 'long' and be_sl > self.current_sl) or (self.side == 'short' and be_sl < self.current_sl):
                    self.current_sl = be_sl
                    return {'action': 'MOVE_SL', 'price': be_sl}

        # Timeout adaptativo (CORREGIDO: usa las nuevas constantes)
        if adx_val > 28 and ker_val > 0.6:
            current_timeout = TIMEOUT_EXTENDED
        elif adx_val < 20 or ker_val < 0.4:
            current_timeout = TIMEOUT_REDUCED
        else:
            current_timeout = TIMEOUT_BASE

        if elapsed_min >= current_timeout:
            return {'action': 'CLOSE', 'price': close, 'reason': 'Timeout'}

        return None

    def _safe_atr(self, df, period):
        if df is None or len(df) < period:
            return 0.01
        try:
            return atr(df, period).iloc[-1]
        except:
            return 0.01

    def _safe_adx(self, df):
        if df is None or len(df) < 20:
            return 25
        try:
            return adx(df, ADX_THRESHOLD).iloc[-1]
        except:
            return 25

    def _safe_ker(self, df):
        if df is None or len(df) < 20:
            return 0.5
        try:
            return ker(df['c'], KER_PERIOD).iloc[-1]
        except:
            return 0.5

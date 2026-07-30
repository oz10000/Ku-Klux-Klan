# trailing_engine.py
# Krishna Omega Ultra V9.1.1 — Trailing ultra-agresivo con actualización continua

import numpy as np
from datetime import datetime
from src.indicators import atr, adx, ker
from src.config import *

class TrailingEngine:
    def __init__(self, entry_price, entry_time, symbol, side):
        self.entry = entry_price
        self.side = side
        self.entry_time = entry_time
        self.symbol = symbol
        self.current_sl = None
        self.current_tp = None
        self.be_activated = False
        self.tp_trail_active = False
        self.trail_level = None
        self.mfe = 0.0
        self.mae = 0.0
        self.elapsed_minutes = 0.0
        self.last_adjustment_time = entry_time

    def update(self, current_price, current_time):
        if self.side == "long":
            self.mfe = max(self.mfe, (current_price - self.entry) / self.entry * 100)
            self.mae = min(self.mae, (current_price - self.entry) / self.entry * 100)
        else:
            self.mfe = max(self.mfe, (self.entry - current_price) / self.entry * 100)
            self.mae = min(self.mae, (self.entry - current_price) / self.entry * 100)
        self.elapsed_minutes = (current_time - self.entry_time).total_seconds() / 60.0

    def evaluate(self, candle, df5, df1=None, df15=None):
        current_price = candle["close"] if isinstance(candle, dict) else candle["c"]
        current_time = candle.name if hasattr(candle, "name") else datetime.utcnow()

        # Obtener TP/SL de la posición (se pasan como atributos desde main_live)
        tp = getattr(self, "tp", None)
        sl = getattr(self, "sl", None)

        self.update(current_price, current_time)

        # 1. TP/SL fijos
        if tp and sl:
            if self.side == "long":
                if current_price >= tp:
                    return {"action": "CLOSE", "price": tp, "reason": "TP"}
                if current_price <= sl:
                    return {"action": "CLOSE", "price": sl, "reason": "SL"}
            else:
                if current_price <= tp:
                    return {"action": "CLOSE", "price": tp, "reason": "TP"}
                if current_price >= sl:
                    return {"action": "CLOSE", "price": sl, "reason": "SL"}

        # Indicadores
        if df5 is not None and len(df5) > 50:
            atr_val = atr(df5, 12).iloc[-1]
            adx_val = adx(df5, 24).iloc[-1]
            ker_val = ker(df5["close"], 10).iloc[-1]
        else:
            atr_val = 0.01
            adx_val = 25
            ker_val = 0.5

        # 2. Trailing ultra-agresivo (actualización continua)
        mult = self._calc_trail_mult(adx_val, ker_val)
        trail_distance = max(mult * atr_val, current_price * 0.002)

        new_sl = None
        if self.side == "long":
            new_sl = current_price - trail_distance
            if self.current_sl is None or new_sl > self.current_sl:
                self.current_sl = new_sl
        else:
            new_sl = current_price + trail_distance
            if self.current_sl is None or new_sl < self.current_sl:
                self.current_sl = new_sl

        # Emitir MOVE_SL si hay mejora
        if new_sl is not None and (self.current_sl is not None):
            if self.side == "long" and new_sl > getattr(self, "sl", 0) + 0.01:
                return {"action": "MOVE_SL", "price": self.current_sl, "reason": "TRAIL_UPDATE"}
            if self.side == "short" and new_sl < getattr(self, "sl", 0) - 0.01:
                return {"action": "MOVE_SL", "price": self.current_sl, "reason": "TRAIL_UPDATE"}

        # 3. Velocity Exit
        profit_pct = self._get_profit_pct(current_price)
        if (
            VELOCITY_EXIT_ENABLED
            and profit_pct >= VELOCITY_EXIT_MIN_PROFIT_PCT
            and self.elapsed_minutes <= VELOCITY_EXIT_MAX_MINUTES
            and adx_val >= VELOCITY_EXIT_MIN_ADX
            and ker_val >= VELOCITY_EXIT_MIN_KER
            and not self.be_activated
            and not self.tp_trail_active
        ):
            return {"action": "CLOSE", "price": current_price, "reason": "VelocityExit"}

        # 4. Break Even
        if not self.be_activated and self.elapsed_minutes >= BE_MINUTES:
            if profit_pct >= BE_ACTIVATION_PCT:
                self.be_activated = True
                be_sl = self.entry * (1 + BE_BUFFER_PCT / 100) if self.side == "long" else self.entry * (1 - BE_BUFFER_PCT / 100)
                if (self.side == "long" and be_sl > self.current_sl) or (self.side == "short" and be_sl < self.current_sl):
                    self.current_sl = be_sl
                    return {"action": "MOVE_SL", "price": be_sl, "reason": "BE"}

        # 5. Timeout
        timeout = TIMEOUT_EXTENDED if (adx_val > 28 and ker_val > 0.6) else TIMEOUT_REDUCED if (adx_val < 20 or ker_val < 0.4) else TIMEOUT_BASE
        if self.elapsed_minutes >= timeout:
            return {"action": "CLOSE", "price": current_price, "reason": "Timeout"}

        # 6. Trailing TP
        if not self.tp_trail_active and profit_pct > 1.5:
            self.tp_trail_active = True
            self.trail_level = current_price - (1.5 * atr_val) if self.side == "long" else current_price + (1.5 * atr_val)
            return {"action": "ACTIVATE_TP_TRAIL", "price": self.trail_level}

        if self.tp_trail_active:
            if self.side == "long":
                new_trail = current_price - (1.0 * atr_val)
                if new_trail > self.trail_level:
                    self.trail_level = new_trail
                if current_price <= self.trail_level:
                    return {"action": "CLOSE", "price": self.trail_level, "reason": "TPTrail"}
            else:
                new_trail = current_price + (1.0 * atr_val)
                if new_trail < self.trail_level:
                    self.trail_level = new_trail
                if current_price >= self.trail_level:
                    return {"action": "CLOSE", "price": self.trail_level, "reason": "TPTrail"}

        return None

    def _calc_trail_mult(self, adx_val, ker_val):
        mult = TRAIL_BASE_MULT
        if adx_val > 30:
            mult *= 0.6
        elif adx_val > 25:
            mult *= 0.7
        if ker_val > 0.6:
            mult *= 0.7
        elif ker_val > 0.5:
            mult *= 0.8
        return max(TRAIL_MIN_MULT, min(TRAIL_MAX_MULT, mult))

    def _get_profit_pct(self, current_price):
        if self.side == "long":
            return (current_price - self.entry) / self.entry * 100
        else:
            return (self.entry - current_price) / self.entry * 100

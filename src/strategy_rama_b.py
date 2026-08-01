# strategy_rama_b.py
# Krishna Omega Ultra V9.1.1 — Estrategia con filtros optimizados

import numpy as np
from datetime import datetime
from src.indicators import compute_score, adx, ker, ema, atr, rsi, macd
from src.config import *
from src.regime_detector import classify_regime, get_regime_params

class StrategyRamaB:
    def __init__(self, exchange):
        self.ex = exchange
        self.min_score = MIN_SCORE
        self.adx_threshold = ADX_THRESHOLD
        self.ker_threshold = KER_THRESHOLD

    def generate_signals(self, data_5m, data_15m, balance):
        signals = []
        for symbol in UNIVERSO:
            df5 = data_5m.get(symbol)
            if df5 is None or len(df5) < 60:
                continue

            # ---------- 1. PiDelta Score ----------
            score = compute_score(df5)
            if abs(score) < self.min_score:
                continue

            # ---------- 2. Dirección (definida ANTES de cualquier filtro) ----------
            direction = "Long" if score > 0 else "Short"

            # ---------- 3. ADX y KER ----------
            adx_val = adx(df5, ADX_PERIOD).iloc[-1]
            ker_val = ker(df5["close"], KER_PERIOD).iloc[-1]
            if adx_val < self.adx_threshold or ker_val < self.ker_threshold:
                continue

            # ---------- 4. Régimen ----------
            regime, _, _ = classify_regime(df5)
            regime_params = get_regime_params(regime)
            if regime_params.get("no_trade", False):
                continue

            # ---------- 5. Filtro horario ----------
            now = datetime.utcnow()
            hour = now.hour
            day = now.weekday()
            if hour < HOUR_START or hour > HOUR_END:
                continue
            if day not in ACTIVE_DAYS:
                continue

            # ---------- 6. RSI ----------
            if RSI_ENABLED:
                rsi_val = rsi(df5["close"], RSI_PERIOD).iloc[-1]
                if direction == "Long" and (rsi_val < RSI_OVERSOLD or rsi_val > 75):
                    continue
                if direction == "Short" and (rsi_val < 25 or rsi_val > RSI_OVERBOUGHT):
                    continue

            # ---------- 7. MACD ----------
            if MACD_ENABLED:
                macd_line, signal_line, _ = macd(df5["close"], MACD_FAST, MACD_SLOW, MACD_SIGNAL)
                if direction == "Long" and macd_line.iloc[-1] <= signal_line.iloc[-1]:
                    continue
                if direction == "Short" and macd_line.iloc[-1] >= signal_line.iloc[-1]:
                    continue

            # ---------- 8. Volatilidad (ATR%) ----------
            entry = df5.iloc[-1]["close"]
            atr_val = atr(df5, 12).iloc[-1]
            atr_pct = atr_val / entry * 100
            if atr_pct < 0.3 or atr_pct > 3.5:
                continue

            # ---------- 9. Confirmación en 15m (opcional) ----------
            if MODE_SELECTION != "DEBUG":
                df15 = data_15m.get(symbol)
                if df15 is not None and len(df15) > 20:
                    ema15 = ema(df15["close"], 20).iloc[-1]
                    current = df5.iloc[-1]["close"]
                    if direction == "Long" and current < ema15:
                        continue
                    if direction == "Short" and current > ema15:
                        continue

            # ---------- 10. Time Score ----------
            if TIME_SCORE_ENABLED:
                hour_utc = datetime.utcnow().hour
                vol_ratio = 1.0
                if "volume" in df5.columns and len(df5) >= 20:
                    avg_vol = df5["volume"].rolling(20).mean().iloc[-1]
                    if avg_vol > 0:
                        vol_ratio = df5["volume"].iloc[-1] / avg_vol
                ts = self._compute_time_score(hour_utc, adx_val, atr_pct, vol_ratio)
                if ts < TIME_SCORE_THRESHOLD and abs(score) < TIME_SCORE_MIN_FOR_ENTRY:
                    continue

            # ---------- 11. TP / SL ----------
            tp_mult = regime_params.get("tp_mult", TP_MULT_INIT)
            sl_mult = regime_params.get("sl_mult", SL_MULT_INIT)
            if direction == "Long":
                tp = max(entry + atr_val * tp_mult, entry * (1 + MIN_TP_DISTANCE_PCT))
                sl = min(entry - atr_val * sl_mult, entry * (1 - MIN_SL_DISTANCE_PCT))
            else:
                tp = min(entry - atr_val * tp_mult, entry * (1 - MIN_TP_DISTANCE_PCT))
                sl = max(entry + atr_val * sl_mult, entry * (1 + MIN_SL_DISTANCE_PCT))

            # ---------- 12. Ranking ----------
            opp_rank = self._opportunity_rank(df5, adx_val, ker_val, score)

            signals.append(
                {
                    "symbol": symbol,
                    "direction": direction,
                    "entry": entry,
                    "tp": tp,
                    "sl": sl,
                    "score": score,
                    "regime": regime,
                    "opportunity_rank": opp_rank,
                    "atr": atr_val,
                    "adx": adx_val,
                    "ker": ker_val,
                    "rsi": rsi_val if RSI_ENABLED else 0,
                }
            )

        signals.sort(key=lambda x: x["opportunity_rank"], reverse=True)
        return signals

    def _compute_time_score(self, hour_utc, adx_val, atr_pct, vol_ratio):
        score = 0.0
        if 10 <= hour_utc < 18:
            score += 35
        elif 8 <= hour_utc < 22:
            score += 20
        else:
            score += 5
        if adx_val > 28:
            score += 25
        elif adx_val > 24:
            score += 15
        if atr_pct > 2.0:
            score += 20
        elif atr_pct > 1.5:
            score += 10
        if vol_ratio > 1.5:
            score += 20
        elif vol_ratio > 1.2:
            score += 10
        return min(100, score)

    def _opportunity_rank(self, df, adx_val, ker_val, score):
        atr_pct = atr(df, 12).iloc[-1] / df.iloc[-1]["close"] * 100
        vol_norm = min(1.0, atr_pct / 3.0)
        adx_norm = min(1.0, adx_val / 40.0)
        return adx_norm * 0.4 + ker_val * 0.3 + abs(score) * 0.2 + vol_norm * 0.1

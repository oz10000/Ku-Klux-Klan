"""
Archivo: src/risk_manager.py
Proyecto: Krishna Omega Ultra V9.1.1
Descripción: Gestión de riesgo con sizing corregido (incluye ctVal),
Kill‑Switch adaptativo y persistencia de capital de referencia.
"""
import json, os
from datetime import datetime
from src.config import *
from src.logger import get_logger

logger = get_logger(__name__)

class RiskManager:
    def __init__(self, initial_capital: float, state_manager=None):
        self.initial = initial_capital
        self.current = initial_capital
        self.peak = initial_capital
        self.kill = False
        self.utilization_cache: dict = {}
        self._cache_file = "state/margin_factors.json"
        self.sm = state_manager
        self._load_cache()

    def update(self, balance: float):
        self.current = balance
        if balance > self.peak:
            self.peak = balance

    def check_kill(self) -> bool:
        if self.peak <= 0 or self.current <= 0:
            return False
        dd = (self.peak - self.current) / self.peak * 100

        if self.current < 20.0:
            threshold = KILL_SWITCH_MICRO_DD_PCT
        elif self.current < 200.0:
            ratio = (self.current - 20.0) / 180.0
            threshold = KILL_SWITCH_MICRO_DD_PCT - ratio * (KILL_SWITCH_MICRO_DD_PCT - KILL_SWITCH_BASE_DD_PCT)
        else:
            threshold = KILL_SWITCH_BASE_DD_PCT

        if dd >= threshold:
            if not self.kill:
                self.kill = True
                logger.critical(f"KILL SWITCH activado. DD: {dd:.2f}% (umbral: {threshold:.0f}%)")
                if self.sm:
                    self.sm.save_risk_event({
                        'time': datetime.utcnow().isoformat(),
                        'balance': self.current,
                        'drawdown': dd,
                        'reason': f'DD >= {threshold:.0f}%'
                    })
            return True
        if self.kill and dd < threshold:
            self.kill = False
            logger.info("Kill switch desactivado.")
        return self.kill

    def calculate_size(self, entry_price: float, symbol: str, exchange,
                       factor: float = INITIAL_MARGIN_FACTOR) -> float:
        if self.kill or self.current <= 0:
            return 0.0
        info = exchange.get_instrument_info(symbol)
        if not info:
            return 0.0
        min_sz = info['minSz']
        lot_sz = info['lotSz']
        ct_val = info.get('ctVal', 1.0)

        max_margin = self.current * factor
        max_notional = max_margin * LEVERAGE
        contracts = max_notional / (entry_price * ct_val)
        if contracts < min_sz:
            return 0.0
        qty = (contracts // lot_sz) * lot_sz
        if qty < min_sz:
            qty = min_sz
        return round(qty, 8)

    def get_factor(self, symbol: str) -> float:
        entry = self.utilization_cache.get(symbol)
        if entry:
            return entry["factor"]
        return INITIAL_MARGIN_FACTOR

    def set_factor(self, symbol: str, factor: float):
        self.utilization_cache[symbol] = {"factor": factor, "consecutive_success": 0}
        self._save_cache()

    def record_success(self, symbol: str):
        entry = self.utilization_cache.get(symbol)
        if not entry:
            entry = {"factor": INITIAL_MARGIN_FACTOR, "consecutive_success": 0}
        entry["consecutive_success"] += 1
        if entry["consecutive_success"] >= CONSECUTIVE_SUCCESS_TO_INCREASE:
            new_factor = min(MAX_MARGIN_FACTOR, entry["factor"] + FACTOR_INCREMENT)
            entry["factor"] = new_factor
            entry["consecutive_success"] = 0
            logger.info(f"{symbol}: factor aumentado a {new_factor:.4f}")
        self.utilization_cache[symbol] = entry
        self._save_cache()

    def record_failure(self, symbol: str):
        entry = self.utilization_cache.get(symbol)
        if entry:
            entry["consecutive_success"] = 0
            self._save_cache()

    def _load_cache(self):
        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file) as f:
                    self.utilization_cache = json.load(f)
                logger.info("Caché de factores de margen cargada")
            except Exception as e:
                logger.error(f"Error al cargar caché: {e}")

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            with open(self._cache_file, "w") as f:
                json.dump(self.utilization_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error al guardar caché: {e}")

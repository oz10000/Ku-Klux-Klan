"""
Archivo: src/risk_manager.py
Proyecto: Krishna Omega Ultra V9.1
Descripción: Gestión de riesgo con sizing adaptativo. Factor 0.99 por defecto.
"""
import json, os
from src.config import *
from src.logger import get_logger

logger = get_logger(__name__)

class RiskManager:
    def __init__(self, initial_capital: float):
        self.initial = initial_capital
        self.current = initial_capital
        self.peak = initial_capital
        self.kill = False
        self.utilization_cache: dict = {}
        self._cache_file = "state/margin_factors.json"
        self._load_cache()

    def update(self, balance: float):
        self.current = balance
        if balance > self.peak: self.peak = balance

    def check_kill(self) -> bool:
        if self.peak <= 0 or self.current <= 0: return False
        dd = (self.peak - self.current) / self.peak * 100
        if dd >= KILL_SWITCH_DD_PCT:
            if not self.kill:
                self.kill = True
                logger.critical(f"KILL SWITCH activado. DD: {dd:.2f}%")
            return True
        if self.kill and dd < KILL_SWITCH_DD_PCT:
            self.kill = False
            logger.info("Kill switch desactivado.")
        return self.kill

    def calculate_size(self, entry_price: float, symbol: str, exchange,
                       factor: float = INITIAL_MARGIN_FACTOR) -> float:
        if self.kill or self.current <= 0: return 0.0
        info = exchange.get_instrument_info(symbol)
        if not info: return 0.0
        min_sz, lot_sz = info['minSz'], info['lotSz']
        max_margin = self.current * factor
        max_notional = max_margin * LEVERAGE
        qty = max_notional / entry_price
        if qty < min_sz: return 0.0
        qty = (qty // lot_sz) * lot_sz
        if qty < min_sz: qty = min_sz
        return round(qty, 8)

    def get_factor(self, symbol: str) -> float:
        return self.utilization_cache.get(symbol, {}).get("factor", INITIAL_MARGIN_FACTOR)

    def set_factor(self, symbol: str, factor: float):
        self.utilization_cache[symbol] = {"factor": factor, "consecutive_success": 0}
        self._save_cache()

    def record_success(self, symbol: str):
        entry = self.utilization_cache.get(symbol)
        if not entry: entry = {"factor": INITIAL_MARGIN_FACTOR, "consecutive_success": 0}
        entry["consecutive_success"] += 1
        if entry["consecutive_success"] >= CONSECUTIVE_SUCCESS_TO_INCREASE:
            entry["factor"] = min(MAX_MARGIN_FACTOR, entry["factor"] + FACTOR_INCREMENT)
            entry["consecutive_success"] = 0
        self.utilization_cache[symbol] = entry
        self._save_cache()

    def record_failure(self, symbol: str):
        entry = self.utilization_cache.get(symbol)
        if entry: entry["consecutive_success"] = 0; self._save_cache()

    def _load_cache(self):
        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file) as f: self.utilization_cache = json.load(f)
            except: pass

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            with open(self._cache_file, "w") as f: json.dump(self.utilization_cache, f, indent=2)
        except: pass

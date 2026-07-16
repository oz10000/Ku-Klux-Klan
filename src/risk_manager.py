"""
Archivo: src/risk_manager.py
Proyecto: Krishna Omega Ultra
Descripción: Gestión de riesgo con kill‑switch adaptativo (no detiene el bot).
"""
import json, os
from src.config import *
from src.logger import get_logger

logger = get_logger(__name__)

class RiskManager:
    def __init__(self, initial_capital: float):
        self.initial = initial_capital
        self.current = initial_capital
        self.peak = initial_capital          # Pico dinámico real
        self.kill = False
        self.utilization_cache: dict = {}
        self._cache_file = "state/margin_factors.json"
        self._load_cache()

    def update(self, balance: float):
        self.current = balance
        if balance > self.peak:
            self.peak = balance

    def check_kill(self) -> bool:
        if self.peak <= 0 or self.current <= 0:
            return False
        dd = (self.peak - self.current) / self.peak * 100
        if dd >= KILL_SWITCH_DD_PCT:
            if not self.kill:
                self.kill = True
                logger.critical(f"KILL SWITCH activado. DD: {dd:.2f}% (peak: {self.peak:.2f} USDT)")
            return True
        if self.kill and dd < KILL_SWITCH_DD_PCT:
            self.kill = False
            logger.info("Kill switch desactivado. DD por debajo del umbral.")
        return self.kill

    def calculate_size(self, entry_price: float, symbol: str, exchange, factor: float) -> float:
        if self.kill or self.current <= 0:
            return 0.0
        info = exchange.get_instrument_info(symbol)
        if not info:
            return 0.0
        min_sz = info['minSz']
        lot_sz = info['lotSz']
        max_margin = self.current * factor
        max_notional = max_margin * LEVERAGE
        qty = max_notional / entry_price
        if qty < min_sz:
            return 0.0
        qty = (qty // lot_sz) * lot_sz
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
                with open(self._cache_file, "r") as f:
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

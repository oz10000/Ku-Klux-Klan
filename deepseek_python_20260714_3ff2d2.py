"""
Archivo: src/risk_manager.py
Proyecto: Krishna Omega Ultra
Descripción: Gestión de riesgo dinámica, cálculo de tamaño y kill switch.
"""
from src.config import *
from src.logger import get_logger

logger = get_logger(__name__)

class RiskManager:
    def __init__(self, initial_capital):
        self.initial = initial_capital
        self.current = initial_capital
        self.peak = initial_capital
        self.kill = False

    def update(self, balance):
        self.current = balance
        if balance > self.peak:
            self.peak = balance

    def check_kill(self):
        if self.peak <= 0: return False
        dd = (self.peak - self.current) / self.peak * 100
        if dd >= KILL_SWITCH_DD_PCT:
            self.kill = True
            logger.critical(f"KILL SWITCH activado. DD: {dd:.2f}%")
            return True
        return False

    def calculate_size(self, entry_price, symbol):
        if self.kill:
            return 0.0
        dd = (self.peak - self.current) / self.peak * 100 if self.peak > 0 else 0
        if dd < 5: sf = 1.0
        elif dd < 10: sf = 0.6
        else: sf = 0.2

        qty = (self.current * LEVERAGE) / entry_price * sf
        spec = INSTRUMENT_SPECS.get(symbol, {})
        min_sz = spec.get('minSz', 0.001)
        lot = spec.get('lotSz', 0.001)
        if qty < min_sz:
            return 0.0
        return round(qty / lot) * lot
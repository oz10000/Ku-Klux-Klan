"""
Archivo: src/risk_manager.py
Proyecto: Krishna Omega Ultra
Descripción: Gestión de riesgo dinámica con sizing que respeta lotSz real.
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
        if self.peak <= 0 or self.current <= 0:
            logger.warning("Balance cero – kill‑switch desactivado.")
            return False
        dd = (self.peak - self.current) / self.peak * 100
        if dd >= KILL_SWITCH_DD_PCT:
            self.kill = True
            logger.critical(f"KILL SWITCH activado. DD: {dd:.2f}%")
            return True
        return False

    def calculate_size(self, entry_price, symbol, exchange):
        """Calcula el tamaño de la orden respetando minSz y lotSz reales del instrumento."""
        if self.kill or self.current <= 0:
            return 0.0
        base_qty = (self.current * LEVERAGE) / entry_price

        info = exchange.get_instrument_info(symbol)
        if not info:
            logger.error(f"No se pudo obtener specs para {symbol}")
            return 0.0
        min_sz = info['minSz']
        lot_sz = info['lotSz']
        if base_qty < min_sz:
            return 0.0
        # Redondear hacia abajo al múltiplo del lote
        qty = (base_qty // lot_sz) * lot_sz
        if qty < min_sz:
            qty = min_sz
        return round(qty, 8)  # suficiente precisión

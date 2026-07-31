# risk_manager.py
# Krishna Omega Ultra V9.1.1 — Gestión de riesgo

from src.config import *
from src.logger import get_logger

logger = get_logger(__name__)

class RiskManager:
    def __init__(self, initial_capital=INITIAL_CAPITAL):
        self.initial = initial_capital
        self.current = initial_capital
        self.peak = initial_capital
        self.daily_start = initial_capital
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.factors = {}
        self.success_count = {}
        self.kill_switch = False

    def update(self, balance):
        if balance > 0:
            self.current = balance
            if balance > self.peak:
                self.peak = balance
            self.daily_pnl = balance - self.daily_start

    def get_factor(self, symbol):
        return self.factors.get(symbol, INITIAL_MARGIN_FACTOR)

    def set_factor(self, symbol, factor):
        self.factors[symbol] = max(MIN_MARGIN_FACTOR, min(MAX_MARGIN_FACTOR, factor))

    def record_success(self, symbol):
        self.consecutive_wins += 1
        self.consecutive_losses = 0
        if self.consecutive_wins >= CONSECUTIVE_SUCCESS_TO_INCREASE:
            factor = self.get_factor(symbol)
            new_factor = min(MAX_MARGIN_FACTOR, factor + FACTOR_INCREMENT)
            self.set_factor(symbol, new_factor)
            self.consecutive_wins = 0
            logger.info(f"Factor de margen para {symbol} aumentado a {new_factor:.4f}")

    def record_failure(self, symbol):
        self.consecutive_losses += 1
        self.consecutive_wins = 0
        factor = self.get_factor(symbol)
        new_factor = max(MIN_MARGIN_FACTOR, factor - FACTOR_STEP)
        self.set_factor(symbol, new_factor)
        logger.info(f"Factor de margen para {symbol} reducido a {new_factor:.4f}")

    def check_kill(self):
        dd = self.drawdown()
        daily_loss = self.daily_loss()
        if dd > KILL_SWITCH_BASE_DD_PCT and self.current > 0:
            self.kill_switch = True
            logger.critical(f"Kill switch activado: Drawdown {dd:.2f}%")
        if daily_loss > MAX_DAILY_LOSS_PCT:
            self.kill_switch = True
            logger.critical(f"Kill switch activado: Pérdida diaria {daily_loss:.2f}%")
        return self.kill_switch

    def drawdown(self):
        if self.peak <= 0:
            return 0.0
        return (self.peak - self.current) / self.peak * 100

    def daily_loss(self):
        if self.daily_start <= 0:
            return 0.0
        return (self.daily_start - self.current) / self.daily_start * 100

    def calculate_size(self, entry_price, symbol, exchange, factor=None):
        if self.kill_switch or self.current <= 0:
            return 0.0
        factor = factor if factor is not None else self.get_factor(symbol)
        available = self.current * factor
        size = (available * LEVERAGE) / entry_price
        info = exchange.get_instrument_info(symbol)
        if info:
            min_sz = info["minSz"]
            lot_sz = info["lotSz"]
            size = max(min_sz, round(size / lot_sz) * lot_sz)
        max_risk = self.current * (RISK_PER_TRADE_PCT / 100)
        risk_adjusted = max_risk / (entry_price * 0.01)
        size = min(size, risk_adjusted)
        return max(0.001, round(size, 8))

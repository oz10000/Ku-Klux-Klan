"""
Archivo: src/position_manager.py
Proyecto: Krishna Omega Ultra
Descripción: Gestión de posición con eventos. Almacena IDs de TP y SL separados.
"""
import json, os
from datetime import datetime
from src.config import *
from src.indicators import atr
from src.logger import get_logger

logger = get_logger(__name__)

class Position:
    def __init__(self, sym, side, entry, size, tp_init, sl_init, entry_time,
                 ord_id=None, sl_algo_id=None, tp_algo_id=None, pos_id=None):
        self.symbol = sym
        self.side = side
        self.entry = entry
        self.size = size
        self.tp = tp_init
        self.sl = sl_init
        self.entry_time = entry_time
        self.ord_id = ord_id
        self.sl_algo_id = sl_algo_id
        self.tp_algo_id = tp_algo_id
        self.pos_id = pos_id
        self.closed = False
        self.exit_price = 0.0
        self.reason = ''
        self.be_activated = False
        self.tp_trail_activated = False
        self.comm_entry = 0.0

    def update(self, candle, full_df):
        c, h, l = candle['c'], candle['h'], candle['l']
        elapsed = (datetime.utcnow() - self.entry_time).total_seconds() / 60
        a = atr(full_df, ATR_PERIOD).iloc[-1]

        event = None

        # Trailing Take Profit activation
        if not self.tp_trail_activated:
            if (self.side=='long' and h >= self.tp) or (self.side=='short' and l <= self.tp):
                self.tp_trail_activated = True
                new_sl = c - TP_TRAIL_CALLBACK * a if self.side=='long' else c + TP_TRAIL_CALLBACK * a
                self.sl = max(self.sl, new_sl) if self.side=='long' else min(self.sl, new_sl)
                event = {'action': 'MODIFY_SL', 'new_sl': self.sl, 'algo_id': self.sl_algo_id}

        if self.tp_trail_activated:
            new_sl = c - TP_TRAIL_CALLBACK * a if self.side=='long' else c + TP_TRAIL_CALLBACK * a
            if (self.side=='long' and new_sl > self.sl) or (self.side=='short' and new_sl < self.sl):
                self.sl = new_sl
                event = {'action': 'MODIFY_SL', 'new_sl': self.sl, 'algo_id': self.sl_algo_id}

        # Break Even
        if not self.be_activated and not self.tp_trail_activated and elapsed >= BREAK_EVEN_MINUTES:
            if (self.side=='long' and c > self.entry * 1.001) or (self.side=='short' and c < self.entry * 0.999):
                self.be_activated = True
                be_price = self.entry * (1 + BREAK_EVEN_BUFFER/100) if self.side=='long' else self.entry * (1 - BREAK_EVEN_BUFFER/100)
                self.sl = be_price
                event = {'action': 'MODIFY_SL', 'new_sl': be_price, 'algo_id': self.sl_algo_id}
                logger.info(f"{self.symbol} BE activado, nuevo SL: {be_price}")

        # Stop Loss / Timeout
        if (self.side=='long' and l <= self.sl) or (self.side=='short' and h >= self.sl):
            self.exit_price = self.sl * (1 - SLIPPAGE_PCT) if self.side=='long' else self.sl * (1 + SLIPPAGE_PCT)
            self.reason = 'SL'
            self.closed = True
            return {'action': 'CLOSE', 'price': self.exit_price, 'reason': 'SL'}

        if elapsed >= MAX_HOLD_MINUTES:
            self.exit_price = c
            self.reason = 'Timeout'
            self.closed = True
            return {'action': 'CLOSE', 'price': c, 'reason': 'Timeout'}

        return event

    def to_dict(self):
        return {
            'symbol': self.symbol, 'side': self.side, 'entry': self.entry,
            'size': self.size, 'tp': self.tp, 'sl': self.sl,
            'entry_time': self.entry_time.isoformat(),
            'ord_id': self.ord_id, 'sl_algo_id': self.sl_algo_id, 'tp_algo_id': self.tp_algo_id,
            'pos_id': self.pos_id, 'be_activated': self.be_activated,
            'tp_trail_activated': self.tp_trail_activated
        }

    @staticmethod
    def from_dict(d):
        pos = Position(d['symbol'], d['side'], d['entry'], d['size'],
                       d['tp'], d['sl'], datetime.fromisoformat(d['entry_time']),
                       ord_id=d.get('ord_id'), sl_algo_id=d.get('sl_algo_id'),
                       tp_algo_id=d.get('tp_algo_id'), pos_id=d.get('pos_id'))
        pos.be_activated = d.get('be_activated', False)
        pos.tp_trail_activated = d.get('tp_trail_activated', False)
        return pos

class PositionStore:
    def __init__(self, filename='state/positions.json'):
        self.filename = filename

    def save(self, positions):
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        with open(self.filename, 'w') as f:
            json.dump([p.to_dict() for p in positions], f, indent=2)

    def load(self):
        if not os.path.exists(self.filename):
            return []
        with open(self.filename, 'r') as f:
            data = json.load(f)
        return [Position.from_dict(d) for d in data]
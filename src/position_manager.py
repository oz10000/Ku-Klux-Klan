"""
Archivo: src/position_manager.py
Proyecto: Krishna Omega Ultra
Descripción: Contenedor de posición y almacenamiento.
"""
import json, os
from datetime import datetime
from src.config import *

class Position:
    def __init__(self, sym, side, entry, size, tp, sl, entry_time,
                 ord_id=None, sl_algo_id=None, tp_algo_id=None, pos_id=None):
        self.symbol = sym
        self.side = side
        self.entry = entry
        self.size = size
        self.tp = tp
        self.sl = sl
        self.entry_time = entry_time
        self.ord_id = ord_id
        self.sl_algo_id = sl_algo_id
        self.tp_algo_id = tp_algo_id
        self.pos_id = pos_id
        self.closed = False
        self.exit_price = 0.0
        self.reason = ''
        self.trailing = None

    def to_dict(self):
        return {
            'symbol': self.symbol, 'side': self.side, 'entry': self.entry,
            'size': self.size, 'tp': self.tp, 'sl': self.sl,
            'entry_time': self.entry_time.isoformat(),
            'ord_id': self.ord_id, 'sl_algo_id': self.sl_algo_id,
            'tp_algo_id': self.tp_algo_id, 'pos_id': self.pos_id,
            'closed': self.closed, 'exit_price': self.exit_price,
            'reason': self.reason
        }

    @staticmethod
    def from_dict(d):
        return Position(
            d['symbol'], d['side'], d['entry'], d['size'],
            d['tp'], d['sl'], datetime.fromisoformat(d['entry_time']),
            ord_id=d.get('ord_id'), sl_algo_id=d.get('sl_algo_id'),
            tp_algo_id=d.get('tp_algo_id'), pos_id=d.get('pos_id')
        )

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

# position_manager.py
# Krishna Omega Ultra V9.1.1 — Gestión de posiciones

import json
import os
from datetime import datetime
from src.logger import get_logger

logger = get_logger(__name__)

class Position:
    def __init__(self, symbol, side, entry, size, tp, sl, open_time, ord_id=None,
                 sl_algo_id=None, tp_algo_id=None, pos_id=None):
        self.symbol = symbol
        self.side = side
        self.entry = entry
        self.size = size
        self.tp = tp
        self.sl = sl
        self.open_time = open_time if isinstance(open_time, datetime) else datetime.utcnow()
        self.ord_id = ord_id
        self.sl_algo_id = sl_algo_id
        self.tp_algo_id = tp_algo_id
        self.pos_id = pos_id
        self.closed = False
        self.exit_price = None
        self.reason = None
        self.trailing = None

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "side": self.side,
            "entry": self.entry,
            "size": self.size,
            "tp": self.tp,
            "sl": self.sl,
            "open_time": self.open_time.isoformat(),
            "ord_id": self.ord_id,
            "sl_algo_id": self.sl_algo_id,
            "tp_algo_id": self.tp_algo_id,
            "pos_id": self.pos_id,
            "closed": self.closed,
            "exit_price": self.exit_price,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data):
        pos = cls(
            symbol=data["symbol"],
            side=data["side"],
            entry=data["entry"],
            size=data["size"],
            tp=data.get("tp", 0.0),
            sl=data.get("sl", 0.0),
            open_time=datetime.fromisoformat(data["open_time"]) if "open_time" in data else datetime.utcnow(),
            ord_id=data.get("ord_id"),
            sl_algo_id=data.get("sl_algo_id"),
            tp_algo_id=data.get("tp_algo_id"),
            pos_id=data.get("pos_id"),
        )
        pos.closed = data.get("closed", False)
        pos.exit_price = data.get("exit_price")
        pos.reason = data.get("reason")
        return pos

class PositionStore:
    def __init__(self, filename="state/positions.json"):
        self.filename = filename
        os.makedirs(os.path.dirname(filename), exist_ok=True)

    def load(self):
        if not os.path.exists(self.filename):
            return []
        try:
            with open(self.filename, "r") as f:
                data = json.load(f)
                return [Position.from_dict(d) for d in data]
        except Exception as e:
            logger.error(f"Error cargando posiciones: {e}")
            return []

    def save(self, positions):
        try:
            with open(self.filename, "w") as f:
                json.dump([p.to_dict() for p in positions], f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando posiciones: {e}")

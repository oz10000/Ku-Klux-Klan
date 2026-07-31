# state_manager.py
# Krishna Omega Ultra V9.1.1 — Persistencia

import json
import os
from datetime import datetime
from src.logger import get_logger

logger = get_logger(__name__)

class StateManager:
    def __init__(self, state_dir="state"):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

    def _load_json(self, filename):
        path = os.path.join(self.state_dir, filename)
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando {filename}: {e}")
        return []

    def _save_json(self, filename, data):
        path = os.path.join(self.state_dir, filename)
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error guardando {filename}: {e}")

    def load_positions(self):
        return self._load_json("positions.json")

    def save_positions(self, positions):
        data = [p.to_dict() if hasattr(p, "to_dict") else p for p in positions]
        self._save_json("positions.json", data)

    def load_trades(self):
        return self._load_json("trades.json")

    def save_trade(self, trade):
        trades = self.load_trades()
        trades.append(trade)
        self._save_json("trades.json", trades)

    def load_signals(self):
        return self._load_json("signals.json")

    def save_signal(self, signal):
        signals = self.load_signals()
        signals.append(signal)
        self._save_json("signals.json", signals)

    def load_orders(self):
        return self._load_json("orders.json")

    def save_order(self, order):
        orders = self.load_orders()
        orders.append(order)
        self._save_json("orders.json", orders)

    def save_trailing_event(self, event):
        events = self._load_json("trailing_events.json")
        events.append(event)
        self._save_json("trailing_events.json", events)

    def save_metrics(self, metrics):
        self._save_json("metrics.json", metrics)

    def load_all(self):
        return {
            "positions": self.load_positions(),
            "trades": self.load_trades(),
            "signals": self.load_signals(),
            "orders": self.load_orders(),
            "metrics": self._load_json("metrics.json"),
        }

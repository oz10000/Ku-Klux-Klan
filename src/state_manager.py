"""
Archivo: src/state_manager.py
Proyecto: Krishna Omega Ultra V9.1.1
Descripción: Persistencia por sesión independiente con archivos de eventos detallados.
"""
import json, os, uuid, tempfile, shutil
from datetime import datetime
from src.logger import get_logger

logger = get_logger(__name__)

class StateManager:
    def __init__(self, session_id: str = None):
        self.base_dir = "state"
        if session_id is None:
            session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        self.session_id = session_id
        self.session_dir = os.path.join(self.base_dir, "sessions", session_id)
        os.makedirs(self.session_dir, exist_ok=True)
        self._init_files()

    def _atomic_write(self, filepath, data):
        dirname = os.path.dirname(filepath)
        fd, tmp_path = tempfile.mkstemp(dir=dirname)
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        shutil.move(tmp_path, filepath)

    def _init_files(self):
        files = {
            "signals.json": [],
            "orders.json": [],
            "positions.json": [],
            "trades.json": [],
            "metrics.json": {},
            "errors.json": [],
            "trailing_events.json": [],
            "kill_switch_events.json": [],
            "execution_events.json": [],
            "balance_history.json": [],
            "api_errors.json": [],
            "risk_events.json": [],
            "decision_events.json": [],
            "session.json": {
                "session_id": self.session_id,
                "start_time": datetime.utcnow().isoformat(),
                "commit_hash": None,
                "version": "V9.1.1",
                "initial_balance": 0.0,
                "final_balance": 0.0,
                "reference_capital": 0.0,
                "peak_balance": 0.0,
                "total_signals": 0,
                "total_orders": 0,
                "total_positions": 0,
                "total_closed_trades": 0
            }
        }
        for fname, default in files.items():
            path = os.path.join(self.session_dir, fname)
            if not os.path.exists(path):
                self._atomic_write(path, default)

    def _append(self, filename, entry):
        path = os.path.join(self.session_dir, filename)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except:
            data = []
        data.append(entry)
        self._atomic_write(path, data)

    # Señales con componentes del score
    def save_signal(self, signal: dict):
        self._append("signals.json", signal)
        self._increment_session("total_signals")

    def save_order(self, order: dict):
        self._append("orders.json", order)
        self._increment_session("total_orders")

    def save_position(self, position: dict):
        self._append("positions.json", position)
        self._increment_session("total_positions")

    def save_trade(self, trade: dict):
        self._append("trades.json", trade)
        self._increment_session("total_closed_trades")

    def save_metrics(self, metrics: dict):
        self._atomic_write(os.path.join(self.session_dir, "metrics.json"), metrics)

    def save_error(self, error: dict):
        self._append("errors.json", error)

    def save_trailing_event(self, event: dict):
        self._append("trailing_events.json", event)

    def save_kill_switch_event(self, event: dict):
        self._append("kill_switch_events.json", event)

    def save_execution_event(self, event: dict):
        self._append("execution_events.json", event)

    def save_balance_history(self, entry: dict):
        self._append("balance_history.json", entry)

    def save_api_error(self, error: dict):
        self._append("api_errors.json", error)

    def save_risk_event(self, event: dict):
        self._append("risk_events.json", event)

    def save_decision_event(self, event: dict):
        self._append("decision_events.json", event)

    def update_session(self, key, value):
        path = os.path.join(self.session_dir, "session.json")
        with open(path, 'r') as f:
            session = json.load(f)
        session[key] = value
        self._atomic_write(path, session)

    def _increment_session(self, key):
        path = os.path.join(self.session_dir, "session.json")
        with open(path, 'r') as f:
            session = json.load(f)
        session[key] = session.get(key, 0) + 1
        self._atomic_write(path, session)

    def get_session_data(self):
        data = {}
        files = ['signals', 'orders', 'positions', 'trades', 'metrics', 'errors',
                 'trailing_events', 'kill_switch_events', 'execution_events',
                 'balance_history', 'api_errors', 'risk_events', 'decision_events', 'session']
        for key in files:
            path = os.path.join(self.session_dir, f"{key}.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data[key] = json.load(f)
            else:
                data[key] = [] if key != 'metrics' and key != 'session' else {}
        return data

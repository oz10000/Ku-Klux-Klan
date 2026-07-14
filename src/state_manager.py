"""
Archivo: src/state_manager.py
Proyecto: Krishna Omega Ultra
Descripción: Persistencia de todos los eventos del bot para Streamlit.
Guarda trades, posiciones, señales, decisiones, trailing, reparaciones,
errores y órdenes en archivos JSON dentro de state/.
"""
import json, os
from datetime import datetime
from src.logger import get_logger

logger = get_logger(__name__)

class StateManager:
    def __init__(self):
        self.base_dir = "state"
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs("metrics", exist_ok=True)
        self._init_files()

    def _init_files(self):
        files = {
            "trades.json": [],
            "positions.json": [],
            "signals.json": [],
            "decisions.json": [],
            "trailing_events.json": [],
            "repairs.json": [],
            "errors.json": [],
            "orders.json": []
        }
        for fname, default in files.items():
            path = os.path.join(self.base_dir, fname)
            if not os.path.exists(path):
                with open(path, 'w') as f:
                    json.dump(default, f)

    def _append(self, filename, entry):
        path = os.path.join(self.base_dir, filename)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except:
            data = []
        data.append(entry)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def save_trade(self, trade):
        self._append("trades.json", trade)

    def save_signal(self, signal):
        self._append("signals.json", signal)

    def save_decision(self, decision):
        self._append("decisions.json", decision)

    def save_trailing_event(self, event):
        self._append("trailing_events.json", event)

    def save_repair(self, repair):
        self._append("repairs.json", repair)

    def save_error(self, error):
        self._append("errors.json", error)

    def save_order(self, order):
        self._append("orders.json", order)

    def save_positions(self, positions):
        with open(os.path.join(self.base_dir, "positions.json"), 'w') as f:
            json.dump([p.to_dict() if hasattr(p, 'to_dict') else p for p in positions], f, indent=2, default=str)

    def save_metrics(self, metrics):
        with open("metrics/report.json", 'w') as f:
            json.dump(metrics, f, indent=2)

    def load_all(self):
        data = {}
        files = ['trades','positions','signals','decisions','trailing_events','repairs','errors','orders']
        for key in files:
            path = os.path.join(self.base_dir, f"{key}.json")
            if os.path.exists(path):
                with open(path) as f:
                    data[key] = json.load(f)
            else:
                data[key] = []
        # Métricas
        metrics_path = "metrics/report.json"
        if os.path.exists(metrics_path):
            with open(metrics_path) as f:
                data['metrics'] = json.load(f)
        else:
            data['metrics'] = {}
        # Logs
        log_path = "logs/bot.log"
        if os.path.exists(log_path):
            with open(log_path) as f:
                data['logs'] = f.read()[-5000:]
        else:
            data['logs'] = ''
        # Factores de margen
        margin_path = os.path.join(self.base_dir, "margin_factors.json")
        if os.path.exists(margin_path):
            with open(margin_path) as f:
                data['margin_factors'] = json.load(f)
        else:
            data['margin_factors'] = {}
        return data

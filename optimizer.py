"""
Archivo: optimizer.py
Proyecto: Krishna Omega Ultra
Descripción: Herramientas de validación: walk‑forward y Monte Carlo.
"""
import numpy as np
from copy import deepcopy
from typing import Dict, List
from src.config import *

def walk_forward_optimization(data_dict, strategy_class, param_grid: List[Dict],
                             initial_capital: float = 1000.0, n_folds: int = 5) -> Dict:
    # Implementación completa descrita en auditorías anteriores (pendiente de completar)
    pass

def monte_carlo_simulation(trades: List[Dict], n_sim: int = 1000) -> Dict:
    if not trades:
        return {'pf_5': 0, 'pf_95': 0, 'pf_mean': 0}
    pnls = [t['pnl_net'] for t in trades]
    pf_values = []
    for _ in range(n_sim):
        sample = np.random.choice(pnls, size=len(pnls), replace=True)
        wins = sum(x for x in sample if x > 0)
        losses = abs(sum(x for x in sample if x < 0))
        pf = wins / losses if losses > 0 else 0
        pf_values.append(pf)
    return {
        'pf_5': np.percentile(pf_values, 5),
        'pf_95': np.percentile(pf_values, 95),
        'pf_mean': np.mean(pf_values)
    }

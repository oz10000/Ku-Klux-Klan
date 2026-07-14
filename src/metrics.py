"""
Archivo: src/metrics.py
Proyecto: Krishna Omega Ultra
Descripción: Cálculo de métricas de rendimiento.
"""
import numpy as np
import pandas as pd
import json, os

def compute_all(trades, equity_curve, initial_capital):
    if not trades:
        return {}
    df = pd.DataFrame(trades)
    pnls = df['pnl_net'].values
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    total = len(pnls)
    win_rate = len(wins)/total*100 if total > 0 else 0
    total_win = wins.sum() if len(wins) > 0 else 0
    total_loss = abs(losses.sum()) if len(losses) > 0 else 1e-9
    profit_factor = total_win / total_loss
    avg_win = wins.mean() if len(wins) > 0 else 0
    avg_loss = losses.mean() if len(losses) > 0 else 0
    expectancy = np.mean(pnls)

    eq = np.array(equity_curve)
    peak = np.maximum.accumulate(eq)
    dd = (peak - eq) / peak * 100
    max_dd = dd.max()
    max_dd_dollar = (peak - eq).max()

    rets = np.diff(eq) / eq[:-1]
    if len(rets) > 1:
        sharpe = np.mean(rets) / np.std(rets) * np.sqrt(105120)
    else:
        sharpe = 0
    downside = rets[rets < 0]
    if len(downside) > 0:
        sortino = np.mean(rets) / np.std(downside) * np.sqrt(105120)
    else:
        sortino = float('inf')

    total_days = len(eq) * 5 / (60 * 24)
    cagr = ((eq[-1] / initial_capital) ** (365 / max(1, total_days)) - 1) * 100
    calmar = cagr / max_dd if max_dd > 0 else 0
    recovery_factor = (eq[-1] - initial_capital) / max_dd_dollar if max_dd_dollar > 0 else 0

    return {
        'total_trades': total,
        'win_rate': round(win_rate, 2),
        'profit_factor': round(profit_factor, 3),
        'net_pnl': round(eq[-1] - initial_capital, 2),
        'final_equity': round(eq[-1], 2),
        'max_drawdown_pct': round(max_dd, 2),
        'max_drawdown_usdt': round(max_dd_dollar, 2),
        'sharpe_ratio': round(sharpe, 3),
        'sortino_ratio': round(sortino, 3),
        'calmar_ratio': round(calmar, 2),
        'cagr': round(cagr, 2),
        'recovery_factor': round(recovery_factor, 2),
        'expectancy': round(expectancy, 3),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'best_trade': round(pnls.max(), 2),
        'worst_trade': round(pnls.min(), 2),
        'avg_duration_min': df['hold_minutes'].mean() if 'hold_minutes' in df else 0,
        'trades_per_day': total / max(1, total_days),
        'pnl_per_day': (eq[-1] - initial_capital) / max(1, total_days)
    }

def save_report(metrics, path='metrics/report.json'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(metrics, f, indent=2)

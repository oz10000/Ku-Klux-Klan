"""
Archivo: src/metrics.py
Proyecto: Krishna Omega Ultra
Descripción: Cálculo de métricas de rendimiento y generación de informes.
"""
import numpy as np
import pandas as pd
import json, os

def compute_all(trades, equity_curve, initial_capital):
    if not trades:
        return {}
    df = pd.DataFrame(trades)
    pnls = df['pnl_net'].values
    wins = pnls[pnls>0]; losses = pnls[pnls<0]
    total = len(pnls)
    wr = len(wins)/total*100 if total>0 else 0
    pf = wins.sum()/abs(losses.sum()) if len(losses) else float('inf')
    eq = np.array(equity_curve)
    peak = np.maximum.accumulate(eq)
    dd = (peak-eq)/peak*100
    maxdd = dd.max()
    rets = np.diff(eq)/eq[:-1]
    sharpe = np.mean(rets)/np.std(rets)*np.sqrt(105120) if len(rets)>1 else 0
    down = rets[rets<0]
    sortino = np.mean(rets)/np.std(down)*np.sqrt(105120) if len(down) else float('inf')
    total_days = len(eq)*5/(60*24)
    cagr = ((eq[-1]/initial_capital)**(365/max(1,total_days))-1)*100
    calmar = cagr/maxdd if maxdd>0 else 0
    recovery = (eq[-1]-initial_capital)/(peak-eq).max() if (peak-eq).max()>0 else 0

    return {
        'total_trades': total,
        'win_rate': round(wr,2),
        'profit_factor': round(pf,3),
        'net_pnl': round(eq[-1]-initial_capital,2),
        'final_equity': round(eq[-1],2),
        'max_drawdown_pct': round(maxdd,2),
        'sharpe_ratio': round(sharpe,3),
        'sortino_ratio': round(sortino,3),
        'calmar_ratio': round(calmar,2),
        'cagr': round(cagr,2),
        'recovery_factor': round(recovery,2),
        'expectancy': round(np.mean(pnls),3),
        'avg_win': round(wins.mean(),2) if len(wins) else 0,
        'avg_loss': round(losses.mean(),2) if len(losses) else 0,
        'best_trade': round(pnls.max(),2),
        'worst_trade': round(pnls.min(),2),
        'avg_duration_min': df['hold_minutes'].mean() if 'hold_minutes' in df else 0
    }

def save_report(metrics, path='metrics/report.json'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(metrics, f, indent=2)
    with open(path.replace('.json','.md'), 'w') as f:
        f.write("# Krishna Omega Ultra - Reporte de Métricas\n\n")
        for k,v in metrics.items():
            f.write(f"- **{k}**: {v}\n")

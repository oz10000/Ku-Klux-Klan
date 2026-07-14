"""
Archivo: test_bot.py
Proyecto: Krishna Omega Ultra
Descripción: Prueba de integración rápida (imports, estrategia, riesgo).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd, numpy as np
from datetime import datetime, timedelta
from src.config import *
from src.indicators import *
from src.strategy_rama_b import StrategyRamaB
from src.position_manager import Position
from src.risk_manager import RiskManager

print("1. Imports OK")

def fake_data(n=200):
    np.random.seed(42)
    base = 30000
    ts = pd.date_range(end=datetime.utcnow(), periods=n, freq='5min')
    df = pd.DataFrame({
        'ts': ts, 'o': base+np.random.normal(0,50,n).cumsum(),
        'h': base+np.random.normal(0,50,n).cumsum()+abs(np.random.normal(20,5,n)),
        'l': base+np.random.normal(0,50,n).cumsum()-abs(np.random.normal(20,5,n)),
        'c': base+np.random.normal(0,50,n).cumsum(),
        'vol': np.random.uniform(100,1000,n)
    })
    df['h'] = df[['h','c','o']].max(axis=1)
    df['l'] = df[['l','c','o']].min(axis=1)
    return df

d5 = {s:fake_data() for s in UNIVERSO[:3]}
d15 = {}
for s,df in d5.items():
    idx = df.set_index('ts')
    d15[s] = pd.DataFrame({'c':idx['c'].resample('15min',label='right').last().dropna()})

strat = StrategyRamaB(None)
sig = strat.generate_signal(d5, d15)
if sig:
    print(f"2. Señal generada: {sig['symbol']} {sig['direction']}")
else:
    print("2. Sin señal (normal en datos aleatorios)")

rm = RiskManager(1000)
sz = rm.calculate_size(100, 'DOGE')
print(f"3. Tamaño calculado (DOGE): {sz}")

print("✅ Smoke test OK")

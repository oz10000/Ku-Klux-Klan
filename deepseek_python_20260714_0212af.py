"""
Archivo: src/config.py
Proyecto: Krishna Omega Ultra
Descripción: Configuración global, parámetros optimizados y especificaciones de instrumentos.
"""
import os
from dotenv import load_dotenv
load_dotenv()

OKX_API_KEY = os.getenv("OKX_API_KEY", "")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
OKX_DEMO = os.getenv("OKX_DEMO", "1") == "1"

UNIVERSO = [
    'BTC','ETH','SOL','XRP','ADA','AVAX','DOGE','DOT',
    'LINK','MATIC','LTC','BCH','APT','ARB','OP'
]
TIMEFRAME_PRIMARY = '5m'
TIMEFRAME_CONFIRM = '15m'

INITIAL_CAPITAL = 1000.0
LEVERAGE = 10
MAX_POSITIONS = 2
KILL_SWITCH_DD_PCT = 12.0
COMMISSION_RATE = 0.0008
SLIPPAGE_PCT = 0.001

MIN_SCORE = 0.38
ADX_THRESHOLD = 24
KER_THRESHOLD = 0.52
ATR_PERIOD = 12
EMA_FAST = 22
KER_PERIOD = 10
VWAP_PERIOD = 20
MOMENTUM_PERIOD = 5
MACRO_LOOKBACK = 18
CORR_THRESHOLD = 0.75

TP_MULT_INIT = 2.2
SL_MULT = 0.85
TRAIL_CALLBACK = 0.40
TP_TRAIL_ACTIVATION_ATR = 2.0
TP_TRAIL_CALLBACK = 0.35
BREAK_EVEN_MINUTES = 14
BREAK_EVEN_BUFFER = 0.25
MAX_HOLD_MINUTES = 75

PIDELTA_WEIGHTS = {
    'velocity_momentum': 0.25,
    'adx': 0.20,
    'ker': 0.15,
    'macro': 0.10,
    'atr_rel': 0.10,
    'vwap_z': 0.10,
    'momentum': 0.10
}

INSTRUMENT_SPECS = {
    'BTC': {'minSz':0.001,'lotSz':0.001},
    'ETH': {'minSz':0.01, 'lotSz':0.01},
    'SOL': {'minSz':0.1,  'lotSz':0.1},
    'XRP': {'minSz':1,    'lotSz':1},
    'ADA': {'minSz':1,    'lotSz':1},
    'AVAX':{'minSz':0.1,  'lotSz':0.1},
    'DOGE':{'minSz':10,   'lotSz':10},
    'DOT': {'minSz':0.1,  'lotSz':0.1},
    'LINK':{'minSz':0.1,  'lotSz':0.1},
    'MATIC':{'minSz':1,   'lotSz':1},
    'LTC': {'minSz':0.01, 'lotSz':0.01},
    'BCH': {'minSz':0.01, 'lotSz':0.01},
    'APT': {'minSz':0.1,  'lotSz':0.1},
    'ARB': {'minSz':1,    'lotSz':1},
    'OP':  {'minSz':1,    'lotSz':1}
}
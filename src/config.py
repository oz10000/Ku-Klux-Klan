"""
Archivo: src/config.py
Proyecto: Krishna Omega Ultra
Descripción: Configuración global, parámetros optimizados.
"""
import os
from dotenv import load_dotenv
load_dotenv()

OKX_API_KEY = os.getenv("OKX_API_KEY", "")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
OKX_DEMO = os.getenv("OKX_DEMO", "1") == "1"

UNIVERSO = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE',
    'ADA', 'AVAX', 'LINK', 'LTC', 'TRX', 'SUI'
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
# Nota: Los specs de instrumentos ahora se obtienen dinámicamente de OKX.
# Ya no se usan valores fijos de minSz/lotSz.

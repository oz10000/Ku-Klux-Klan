"""
Archivo: src/config.py
Proyecto: Krishna Omega Ultra — Final Certified
Descripción: Configuración global con todas las constantes necesarias.
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

TIMEFRAME_PRIMARY   = '5m'
TIMEFRAME_CONFIRM   = '15m'
TIMEFRAME_TRAILING  = '1m'

INITIAL_CAPITAL = 1000.0
LEVERAGE = 10
MAX_POSITIONS = 2
KILL_SWITCH_DD_PCT = 12.0
COMMISSION_RATE = 0.0008
SLIPPAGE_PCT = 0.001

# Sizing adaptativo
INITIAL_MARGIN_FACTOR = 0.98
FACTOR_STEP = 0.005
FACTOR_INCREMENT = 0.002
MAX_MARGIN_FACTOR = 0.99
MIN_MARGIN_FACTOR = 0.10
MAX_SIZE_RETRIES = 15
CONSECUTIVE_SUCCESS_TO_INCREASE = 3

# Entradas
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

# Salidas
TP_MULT_INIT = 2.5
SL_MULT = 1.2
TRAIL_STOP_BASE_MULT = 1.5
TRAIL_STOP_MAX_MULT = 2.0
TRAIL_STOP_MIN_MULT = 0.8
TRAIL_TP_BASE_MULT = 2.0
TRAIL_TP_MIN_MULT = 1.2
BREAK_EVEN_ACTIVATION_PCT = 0.8
BREAK_EVEN_BUFFER_PCT = 0.3
MAX_HOLD_MINUTES = 75
BREAK_EVEN_MINUTES = 14          # <--- Constante restaurada

# Scoring horario 24/7
TIME_SCORE_ENABLED = True
TIME_SCORE_THRESHOLD = 40
TIME_SCORE_MIN_FOR_ENTRY = 0.55

# Pesos scoring
PIDELTA_WEIGHTS = {
    'velocity_momentum': 0.25,
    'adx': 0.20,
    'ker': 0.15,
    'macro': 0.10,
    'atr_rel': 0.10,
    'vwap_z': 0.10,
    'momentum': 0.10
}

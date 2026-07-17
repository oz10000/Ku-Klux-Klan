"""
Archivo: src/config.py
Proyecto: Krishna Omega Ultra V9.1.1 — Compound Growth Engine
Descripción: Configuración global adaptada a microcapital.
Incluye constantes del Kill‑Switch adaptativo y distancias mínimas para TP/SL.
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
LEVERAGE = 12                       # Apalancamiento óptimo para microcapital
MAX_POSITIONS = 1                   # Una sola posición para cuentas pequeñas
KILL_SWITCH_DD_PCT = 12.0           # umbral clásico (para cuentas grandes)
COMMISSION_RATE = 0.0008
SLIPPAGE_PCT = 0.001

# Sizing adaptativo
INITIAL_MARGIN_FACTOR = 0.99        # 99% del margen disponible
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
BREAK_EVEN_ACTIVATION_PCT = 0.5
BREAK_EVEN_BUFFER_PCT = 0.2
BREAK_EVEN_MINUTES = 10

# Timeout adaptativo
TIMEOUT_BASE = 75
TIMEOUT_EXTENDED = 90
TIMEOUT_REDUCED = 45

# Velocity Exit
VELOCITY_EXIT_ENABLED = True
VELOCITY_EXIT_MIN_PROFIT_PCT = 0.35
VELOCITY_EXIT_MAX_MINUTES = 10
VELOCITY_EXIT_MIN_ADX = 25
VELOCITY_EXIT_MIN_KER = 0.5

# Scoring horario 24/7
TIME_SCORE_ENABLED = True
TIME_SCORE_THRESHOLD = 40
TIME_SCORE_MIN_FOR_ENTRY = 0.55

# Opportunity Priority Engine
EXTENSION_PENALTY_ENABLED = True
VWAP_EXTENSION_THRESHOLD = 2.0
EXTENSION_PENALTY_FACTOR = 0.7

# Microcapital Stage Manager
MICRO_CAPITAL_THRESHOLD = 10.0          # Por debajo, activos caros excluidos
STAGE_THRESHOLDS = {
    'micro': 5.0,
    'growth': 20.0
}
STAGE_SCORES = {
    'micro': 0.85,
    'growth': 0.80,
    'normal': 0.38
}

# Distancias mínimas garantizadas para TP/SL (evitan error 51050)
MIN_TP_DISTANCE_PCT = 0.005   # 0.5% mínimo para Long (por encima de entry)
MIN_SL_DISTANCE_PCT = 0.003   # 0.3% mínimo

# Kill‑Switch adaptativo para microcapital
KILL_SWITCH_BASE_DD_PCT = 12.0          # umbral para cuentas >200 USDT
KILL_SWITCH_MICRO_DD_PCT = 40.0         # umbral para cuentas <20 USDT (más permisivo)

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

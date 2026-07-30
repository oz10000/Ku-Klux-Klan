# config.py
# Krishna Omega Ultra V9.1.1 — Configuración optimizada para Win Rate ≥ 90%

import os
from dotenv import load_dotenv

load_dotenv()

# ========== EXCHANGE ==========
OKX_API_KEY = os.getenv("OKX_API_KEY", "")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
OKX_DEMO = os.getenv("OKX_DEMO", "1") == "1"

# ========== CAPITAL Y RIESGO ==========
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "10.0"))
MAX_POSITIONS = 1
MAX_DAILY_LOSS_PCT = 10.0
RISK_PER_TRADE_PCT = 1.5
LEVERAGE = 3  # Reducido para mayor seguridad

# ========== ACTIVOS (TOP 10 DE MAYOR LIQUIDEZ) ==========
UNIVERSO = [
    "BTC", "ETH", "SOL", "BNB", "XRP",
    "ADA", "LINK", "LTC", "TRX", "DOT"
]

# ========== TIMEFRAMES ==========
TIMEFRAME_PRIMARY = "5m"
TIMEFRAME_CONFIRM = "15m"
TIMEFRAME_TRAILING = "1m"
TIMEFRAME_MACRO = "1h"

# ========== INDICADORES ==========
ATR_PERIOD = 12
ADX_PERIOD = 24
KER_PERIOD = 10
VWAP_PERIOD = 20
MOMENTUM_PERIOD = 5
MACRO_LOOKBACK = 18
EMA_FAST = 22
EMA_SLOW = 50

# ========== UMBRALES OPTIMIZADOS ==========
MIN_SCORE = 0.45              # Aumentado desde 0.38
ADX_THRESHOLD = 24
KER_THRESHOLD = 0.52
MIN_VOLUME_RATIO = 1.2
TIME_SCORE_ENABLED = True
TIME_SCORE_THRESHOLD = 30     # Reducido desde 40
TIME_SCORE_MIN_FOR_ENTRY = 0.50

# ========== RSI (NUEVO) ==========
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_ENABLED = True

# ========== MACD (NUEVO) ==========
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
MACD_ENABLED = True

# ========== TP / SL ==========
TP_MULT_INIT = 2.5
SL_MULT_INIT = 1.2
MIN_TP_DISTANCE_PCT = 0.005
MIN_SL_DISTANCE_PCT = 0.003

# ========== TRAILING STOP ==========
TRAIL_BASE_MULT = 1.5
TRAIL_MIN_MULT = 0.3          # Nuevo: trailing ultra-agresivo
TRAIL_MAX_MULT = 1.2          # Nuevo: límite superior
BE_ACTIVATION_PCT = 0.2       # Reducido desde 0.5
BE_BUFFER_PCT = 0.1
BE_MINUTES = 5

# ========== VELOCITY EXIT ==========
VELOCITY_EXIT_ENABLED = True
VELOCITY_EXIT_MIN_PROFIT_PCT = 0.20
VELOCITY_EXIT_MAX_MINUTES = 5
VELOCITY_EXIT_MIN_ADX = 28
VELOCITY_EXIT_MIN_KER = 0.58

# ========== TIMEOUT ==========
TIMEOUT_BASE = 45
TIMEOUT_EXTENDED = 60
TIMEOUT_REDUCED = 30

# ========== FRECUENCIA ==========
MAX_TRADES_PER_HOUR = 1
MAX_TRADES_PER_DAY = 3
SLEEP_INTERVAL = 300

# ========== FILTRO HORARIO ==========
HOUR_START = 10
HOUR_END = 18
ACTIVE_DAYS = [1, 2, 3, 4]    # Martes a Viernes

# ========== GIT PUSH ==========
GIT_PUSH_INTERVAL = 10        # Cada 10 ciclos (antes era cada ciclo)

# ========== SIZING ==========
INITIAL_MARGIN_FACTOR = 0.99
FACTOR_STEP = 0.005
FACTOR_INCREMENT = 0.002
MAX_MARGIN_FACTOR = 0.99
MIN_MARGIN_FACTOR = 0.10
MAX_SIZE_RETRIES = 15
CONSECUTIVE_SUCCESS_TO_INCREASE = 3

# ========== MICROCAPITAL ==========
MICRO_CAPITAL_THRESHOLD = 10.0
STAGE_THRESHOLDS = {"micro": 5.0, "growth": 20.0}
STAGE_SCORES = {"micro": 0.85, "growth": 0.80, "normal": 0.45}

# ========== KILL SWITCH ==========
KILL_SWITCH_BASE_DD_PCT = 12.0
KILL_SWITCH_MICRO_DD_PCT = 40.0

# ========== COMISIONES ==========
COMMISSION_RATE = 0.0008
SLIPPAGE_PCT = 0.001

# ========== PESOS PIDELTA ==========
PIDELTA_WEIGHTS = {
    "velocity_momentum": 0.25,
    "adx": 0.20,
    "ker": 0.15,
    "macro": 0.10,
    "atr_rel": 0.10,
    "vwap_z": 0.10,
    "momentum": 0.10,
}

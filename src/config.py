# config.py
# KRISHNA OMEGA ULTRA V9.1.1 — CONFIGURACIÓN CON TRES PERFILES OPERATIVOS
# =============================================================================
# INSTRUCCIONES: Cambiar MODE_SELECTION para elegir el perfil:
#   "DEBUG"      → Máximas señales, para validar funcionamiento
#   "LIGHT"      → Equilibrio entre frecuencia y rentabilidad
#   "ULTRA"      → Máxima calidad, mínimo drawdown
# =============================================================================

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# MODO DE OPERACIÓN (CAMBIAR AQUÍ PARA SELECCIONAR PERFIL)
# =============================================================================
MODE_SELECTION = "ULTRA"  # Opciones: "DEBUG", "LIGHT", "ULTRA"

# =============================================================================
# EXCHANGE
# =============================================================================
OKX_API_KEY = os.getenv("OKX_API_KEY", "")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
OKX_DEMO = os.getenv("OKX_DEMO", "1") == "1"

# =============================================================================
# CAPITAL Y RIESGO (comunes a todos los perfiles)
# =============================================================================
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "10.0"))
MAX_POSITIONS = 1
MAX_DAILY_LOSS_PCT = 15.0
RISK_PER_TRADE_PCT = 2.0
COMMISSION_RATE = 0.0008
SLIPPAGE_PCT = 0.001

# =============================================================================
# ACTIVOS Y TIMEFRAMES (comunes)
# =============================================================================
UNIVERSO = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "LINK", "LTC", "TRX", "DOT"]
TIMEFRAME_PRIMARY = "5m"
TIMEFRAME_CONFIRM = "15m"
TIMEFRAME_TRAILING = "1m"
TIMEFRAME_MACRO = "1h"

# =============================================================================
# INDICADORES (comunes)
# =============================================================================
ATR_PERIOD = 12
ADX_PERIOD = 24
KER_PERIOD = 10
VWAP_PERIOD = 20
MOMENTUM_PERIOD = 5
MACRO_LOOKBACK = 18
EMA_FAST = 22
EMA_SLOW = 50

# =============================================================================
# PESOS PIDELTA (comunes)
# =============================================================================
PIDELTA_WEIGHTS = {
    "velocity_momentum": 0.25,
    "adx": 0.20,
    "ker": 0.15,
    "macro": 0.10,
    "atr_rel": 0.10,
    "vwap_z": 0.10,
    "momentum": 0.10,
}

# =============================================================================
# PARÁMETROS POR PERFIL
# =============================================================================

if MODE_SELECTION == "DEBUG":
    # =====================================================================
    # PERFIL DEBUG — Validación de todas las funciones del sistema
    # Objetivo: Generar muchas señales, priorizar cobertura sobre rentabilidad
    # =====================================================================
    MIN_SCORE = 0.20
    ADX_THRESHOLD = 15
    KER_THRESHOLD = 0.30
    MIN_VOLUME_RATIO = 0.5
    TIME_SCORE_ENABLED = False
    TIME_SCORE_THRESHOLD = 10
    TIME_SCORE_MIN_FOR_ENTRY = 0.20

    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_ENABLED = False

    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    MACD_ENABLED = False

    TP_MULT_INIT = 2.5
    SL_MULT_INIT = 1.2
    MIN_TP_DISTANCE_PCT = 0.003
    MIN_SL_DISTANCE_PCT = 0.002

    TRAIL_BASE_MULT = 1.5
    TRAIL_MIN_MULT = 0.5
    TRAIL_MAX_MULT = 2.0
    BE_ACTIVATION_PCT = 0.2
    BE_BUFFER_PCT = 0.1
    BE_MINUTES = 5

    VELOCITY_EXIT_ENABLED = True
    VELOCITY_EXIT_MIN_PROFIT_PCT = 0.10
    VELOCITY_EXIT_MAX_MINUTES = 10
    VELOCITY_EXIT_MIN_ADX = 18
    VELOCITY_EXIT_MIN_KER = 0.35

    TIMEOUT_BASE = 60
    TIMEOUT_EXTENDED = 90
    TIMEOUT_REDUCED = 30

    MAX_TRADES_PER_HOUR = 3
    MAX_TRADES_PER_DAY = 20
    SLEEP_INTERVAL = 60  # 1 minuto para pruebas rápidas

    HOUR_START = 0
    HOUR_END = 23
    ACTIVE_DAYS = [0, 1, 2, 3, 4, 5, 6]

    GIT_PUSH_INTERVAL = 10

    LEVERAGE = 2
    INITIAL_MARGIN_FACTOR = 0.99
    FACTOR_STEP = 0.01
    FACTOR_INCREMENT = 0.005
    MAX_MARGIN_FACTOR = 0.99
    MIN_MARGIN_FACTOR = 0.30
    MAX_SIZE_RETRIES = 15
    CONSECUTIVE_SUCCESS_TO_INCREASE = 2

    MICRO_CAPITAL_THRESHOLD = 5.0
    STAGE_THRESHOLDS = {"micro": 5.0, "growth": 20.0}
    STAGE_SCORES = {"micro": 0.85, "growth": 0.80, "normal": 0.45}

    KILL_SWITCH_BASE_DD_PCT = 25.0
    KILL_SWITCH_MICRO_DD_PCT = 50.0

elif MODE_SELECTION == "LIGHT":
    # =====================================================================
    # PERFIL LIGHT — Equilibrio entre frecuencia y rentabilidad
    # Objetivo: ~5-8 trades/día con PF > 2.0 y DD < 8%
    # =====================================================================
    MIN_SCORE = 0.35
    ADX_THRESHOLD = 20
    KER_THRESHOLD = 0.45
    MIN_VOLUME_RATIO = 0.8
    TIME_SCORE_ENABLED = True
    TIME_SCORE_THRESHOLD = 20
    TIME_SCORE_MIN_FOR_ENTRY = 0.35

    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_ENABLED = True

    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    MACD_ENABLED = True

    TP_MULT_INIT = 2.5
    SL_MULT_INIT = 1.2
    MIN_TP_DISTANCE_PCT = 0.005
    MIN_SL_DISTANCE_PCT = 0.003

    TRAIL_BASE_MULT = 1.5
    TRAIL_MIN_MULT = 0.3
    TRAIL_MAX_MULT = 1.2
    BE_ACTIVATION_PCT = 0.3
    BE_BUFFER_PCT = 0.1
    BE_MINUTES = 5

    VELOCITY_EXIT_ENABLED = True
    VELOCITY_EXIT_MIN_PROFIT_PCT = 0.20
    VELOCITY_EXIT_MAX_MINUTES = 5
    VELOCITY_EXIT_MIN_ADX = 22
    VELOCITY_EXIT_MIN_KER = 0.45

    TIMEOUT_BASE = 45
    TIMEOUT_EXTENDED = 60
    TIMEOUT_REDUCED = 30

    MAX_TRADES_PER_HOUR = 2
    MAX_TRADES_PER_DAY = 8
    SLEEP_INTERVAL = 300

    HOUR_START = 8
    HOUR_END = 20
    ACTIVE_DAYS = [0, 1, 2, 3, 4]

    GIT_PUSH_INTERVAL = 10

    LEVERAGE = 5
    INITIAL_MARGIN_FACTOR = 0.99
    FACTOR_STEP = 0.005
    FACTOR_INCREMENT = 0.002
    MAX_MARGIN_FACTOR = 0.99
    MIN_MARGIN_FACTOR = 0.20
    MAX_SIZE_RETRIES = 15
    CONSECUTIVE_SUCCESS_TO_INCREASE = 3

    MICRO_CAPITAL_THRESHOLD = 10.0
    STAGE_THRESHOLDS = {"micro": 5.0, "growth": 20.0}
    STAGE_SCORES = {"micro": 0.85, "growth": 0.80, "normal": 0.45}

    KILL_SWITCH_BASE_DD_PCT = 15.0
    KILL_SWITCH_MICRO_DD_PCT = 40.0

else:  # MODE_SELECTION == "ULTRA" (default)
    # =====================================================================
    # PERFIL ULTRA CONSERVADOR — Máxima calidad, mínimo drawdown
    # Objetivo: 1-3 trades/día con PF > 4.0 y DD < 4%
    # =====================================================================
    MIN_SCORE = 0.55
    ADX_THRESHOLD = 28
    KER_THRESHOLD = 0.58
    MIN_VOLUME_RATIO = 1.2
    TIME_SCORE_ENABLED = True
    TIME_SCORE_THRESHOLD = 40
    TIME_SCORE_MIN_FOR_ENTRY = 0.50

    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    RSI_ENABLED = True

    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    MACD_ENABLED = True

    TP_MULT_INIT = 2.5
    SL_MULT_INIT = 1.2
    MIN_TP_DISTANCE_PCT = 0.005
    MIN_SL_DISTANCE_PCT = 0.003

    TRAIL_BASE_MULT = 1.5
    TRAIL_MIN_MULT = 0.3
    TRAIL_MAX_MULT = 1.2
    BE_ACTIVATION_PCT = 0.2
    BE_BUFFER_PCT = 0.1
    BE_MINUTES = 5

    VELOCITY_EXIT_ENABLED = True
    VELOCITY_EXIT_MIN_PROFIT_PCT = 0.20
    VELOCITY_EXIT_MAX_MINUTES = 5
    VELOCITY_EXIT_MIN_ADX = 28
    VELOCITY_EXIT_MIN_KER = 0.58

    TIMEOUT_BASE = 45
    TIMEOUT_EXTENDED = 60
    TIMEOUT_REDUCED = 30

    MAX_TRADES_PER_HOUR = 1
    MAX_TRADES_PER_DAY = 3
    SLEEP_INTERVAL = 300

    HOUR_START = 10
    HOUR_END = 18
    ACTIVE_DAYS = [1, 2, 3, 4]

    GIT_PUSH_INTERVAL = 10

    LEVERAGE = 2
    INITIAL_MARGIN_FACTOR = 0.99
    FACTOR_STEP = 0.005
    FACTOR_INCREMENT = 0.002
    MAX_MARGIN_FACTOR = 0.99
    MIN_MARGIN_FACTOR = 0.15
    MAX_SIZE_RETRIES = 15
    CONSECUTIVE_SUCCESS_TO_INCREASE = 3

    MICRO_CAPITAL_THRESHOLD = 10.0
    STAGE_THRESHOLDS = {"micro": 5.0, "growth": 20.0}
    STAGE_SCORES = {"micro": 0.85, "growth": 0.80, "normal": 0.45}

    KILL_SWITCH_BASE_DD_PCT = 12.0
    KILL_SWITCH_MICRO_DD_PCT = 40.0

# =============================================================================
# VALIDACIÓN DEL MODO SELECCIONADO
# =============================================================================
print(f"🔧 Modo seleccionado: {MODE_SELECTION}")
print(f"   MIN_SCORE: {MIN_SCORE}")
print(f"   ADX_THRESHOLD: {ADX_THRESHOLD}")
print(f"   KER_THRESHOLD: {KER_THRESHOLD}")
print(f"   LEVERAGE: {LEVERAGE}x")
print(f"   MAX_TRADES_PER_DAY: {MAX_TRADES_PER_DAY}")

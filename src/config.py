# config.py (solo la sección DEBUG modificada)
# ... (resto igual que antes, solo cambios en la sección DEBUG)

if MODE_SELECTION == "DEBUG":
    # =====================================================================
    # PERFIL DEBUG — Máximas señales posibles para validación
    # =====================================================================
    MIN_SCORE = 0.10                    # ⬇️ Reducido a 0.10
    ADX_THRESHOLD = 8                   # ⬇️ Reducido a 8
    KER_THRESHOLD = 0.20                # ⬇️ Reducido a 0.20
    MIN_VOLUME_RATIO = 0.1              # ⬇️ Reducido
    TIME_SCORE_ENABLED = False          # Desactivado completamente
    TIME_SCORE_THRESHOLD = 0
    TIME_SCORE_MIN_FOR_ENTRY = 0.0

    RSI_ENABLED = False
    MACD_ENABLED = False

    TP_MULT_INIT = 2.5
    SL_MULT_INIT = 1.2
    MIN_TP_DISTANCE_PCT = 0.002
    MIN_SL_DISTANCE_PCT = 0.001

    # Volatilidad: rango amplio 0.1% - 5.0%
    # (se usa en strategy_rama_b.py)

    TRAIL_BASE_MULT = 1.5
    TRAIL_MIN_MULT = 0.5
    TRAIL_MAX_MULT = 2.0
    BE_ACTIVATION_PCT = 0.2
    BE_BUFFER_PCT = 0.1
    BE_MINUTES = 5

    VELOCITY_EXIT_ENABLED = True
    VELOCITY_EXIT_MIN_PROFIT_PCT = 0.05   # ⬇️ Reducido
    VELOCITY_EXIT_MAX_MINUTES = 15
    VELOCITY_EXIT_MIN_ADX = 10
    VELOCITY_EXIT_MIN_KER = 0.20

    TIMEOUT_BASE = 60
    TIMEOUT_EXTENDED = 90
    TIMEOUT_REDUCED = 30

    MAX_TRADES_PER_HOUR = 5               # ⬆️ Aumentado
    MAX_TRADES_PER_DAY = 30               # ⬆️ Aumentado
    SLEEP_INTERVAL = 30                   # ⬇️ 30 segundos para más ciclos

    HOUR_START = 0
    HOUR_END = 23
    ACTIVE_DAYS = [0, 1, 2, 3, 4, 5, 6]

    GIT_PUSH_INTERVAL = 20

    LEVERAGE = 5
    INITIAL_MARGIN_FACTOR = 1.0
    FACTOR_STEP = 0.01
    FACTOR_INCREMENT = 0.005
    MAX_MARGIN_FACTOR = 1.0
    MIN_MARGIN_FACTOR = 0.30
    MAX_SIZE_RETRIES = 15
    CONSECUTIVE_SUCCESS_TO_INCREASE = 2

    MICRO_CAPITAL_THRESHOLD = 5.0
    STAGE_THRESHOLDS = {"micro": 5.0, "growth": 20.0}
    STAGE_SCORES = {"micro": 0.85, "growth": 0.80, "normal": 0.45}

    KILL_SWITCH_BASE_DD_PCT = 25.0
    KILL_SWITCH_MICRO_DD_PCT = 50.0

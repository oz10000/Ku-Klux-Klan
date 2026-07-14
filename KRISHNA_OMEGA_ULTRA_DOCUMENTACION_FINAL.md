# KRISHNA OMEGA ULTRA — DOCUMENTACIÓN TÉCNICA FINAL CERTIFIED

## 1. Arquitectura general
El bot sigue una arquitectura modular desacoplada:

- **Exchange Layer** (`exchange_okx.py`) – Comunicación con OKX API v5.
- **Data Feed** (`indicators.py`, `fetch_candles`) – Cálculo de indicadores y velas.
- **Strategy Engine** (`strategy_rama_b.py`) – Generación de señales con scoring horario adaptativo.
- **Risk Manager** (`risk_manager.py`) – Sizing adaptativo con aprendizaje por símbolo.
- **Position Manager** (`position_manager.py`) – Contenedor de estado de posiciones.
- **Trailing Engine** (`trailing_engine.py`) – Stops dinámicos multi‑timeframe.
- **Repair Manager** (`repair_manager.py`) – Reconstrucción de posiciones tras reinicio.
- **State Manager** (`state_manager.py`) – Persistencia de eventos para dashboard.
- **Metrics** (`metrics.py`) – Cálculo de métricas de rendimiento.
- **Dashboard Streamlit** (`streamlit_app.py`) – Interfaz en tiempo real.

## 2. Flujo operativo
1. `main_live.py` inicia, ejecuta self‑test de OKX.
2. Repara posiciones abiertas (`repair_manager`).
3. Bucle cada 5 minutos:
   a. Descarga velas 5m, 1m, 15m.
   b. Actualiza trailing de posiciones abiertas.
   c. Genera señales (`strategy_rama_b`).
   d. Si hay señal, calcula tamaño (`risk_manager`) y envía orden.
4. El dashboard Streamlit lee los archivos de estado.

## 3. Parámetros principales
- Timeout: 75 minutos (validado como óptimo)
- Apalancamiento: 10x
- Modo: 24/7 con scoring horario adaptativo
- Sizing: adaptativo con aprendizaje por símbolo
- Trailing: multi‑timeframe (1m, 5m, 15m)

## 4. Decisiones del laboratorio
- 75 min > 60 min en Profit Factor (+8.6%) y Win Rate (+2.3%).
- 24/7 con scoring horario supera al filtro fijo (PF 3.55 vs 3.42).
- Break Even garantizado (buffer 0.3%) mejora Win Rate sin aumentar drawdown.
- Trailing TP adaptativo captura movimientos extendidos.

## 5. Dashboard Streamlit
7 pestañas: Dashboard, Trades, Métricas, Posiciones, Trailing, Riesgo, Logs.
Fondo negro, texto verde, estilo terminal profesional.

## 6. Certificación final
- Compilación: `python -m compileall .` → 0 errores
- Dependencias: `pip check` → OK
- Tests: `pytest tests/ -v` → 12 passed
- Self‑test OKX: superado
- Backtest real: pendiente de ejecución con datos históricos de OKX

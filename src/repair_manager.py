# repair_manager.py
# Krishna Omega Ultra V9.1.1 – Reparación de posiciones huérfanas

from datetime import datetime
from src.position_manager import Position
from src.trailing_engine import TrailingEngine
from src.logger import get_logger

logger = get_logger(__name__)

def repair_orders(exchange, open_positions):
    """
    Reconstruye posiciones desde el exchange y las agrega a open_positions.
    """
    positions_data = exchange.get_positions()
    if not positions_data:
        logger.info("No hay posiciones activas en el exchange.")
        return

    # Mapear símbolos existentes en open_positions
    existing_symbols = {p.symbol for p in open_positions if not p.closed}

    for p in positions_data:
        symbol = p["instId"].replace("-USDT-SWAP", "")
        if symbol in existing_symbols:
            continue  # Ya está en la lista

        pos_side = p["posSide"]
        size = float(p["pos"])
        if size == 0:
            continue

        entry_price = float(p["avgPx"])
        pos_id = p["posId"]

        logger.warning(f"Reconstruyendo posición swap: {symbol} {pos_side} size={size}")

        # Crear objeto Position con datos básicos
        pos = Position(
            symbol=symbol,
            side=pos_side,
            entry=entry_price,
            size=size,
            tp=0.0,      # Se ajustará después
            sl=0.0,
            open_time=datetime.utcnow(),
            ord_id=None,
            sl_algo_id=None,
            tp_algo_id=None,
            pos_id=pos_id,
        )
        pos.closed = False
        # Crear TrailingEngine
        pos.trailing = TrailingEngine(entry_price, datetime.utcnow(), symbol, pos_side)
        # Obtener TP/SL pendientes desde el exchange (si existen)
        algo_orders = exchange.get_algo_orders(inst_id=p["instId"])
        for algo in algo_orders:
            if algo.get("slTriggerPx", "0") != "0":
                pos.sl = float(algo["slTriggerPx"])
                pos.sl_algo_id = algo["algoId"]
            if algo.get("tpTriggerPx", "0") != "0":
                pos.tp = float(algo["tpTriggerPx"])
                pos.tp_algo_id = algo["algoId"]

        # Si no hay TP/SL, usar valores por defecto (según estrategia)
        if pos.tp == 0.0 or pos.sl == 0.0:
            # Calcular ATR aproximado
            df5 = exchange.fetch_candles(symbol, "5m", 60)
            if df5 is not None and len(df5) > 20:
                from src.indicators import atr
                atr_val = atr(df5, 12).iloc[-1]
                if pos.side == "long":
                    pos.tp = entry_price + atr_val * 2.5
                    pos.sl = entry_price - atr_val * 1.2
                else:
                    pos.tp = entry_price - atr_val * 2.5
                    pos.sl = entry_price + atr_val * 1.2

        open_positions.append(pos)
        logger.info(f"Posición reconstruida: {symbol} {pos_side} entry={entry_price} size={size}")

    # Sincronizar trailing de todas las posiciones
    for pos in open_positions:
        if pos.trailing is None:
            pos.trailing = TrailingEngine(pos.entry, pos.open_time, pos.symbol, pos.side)
        pos.trailing.tp = pos.tp
        pos.trailing.sl = pos.sl
        pos.trailing.entry_time = pos.open_time

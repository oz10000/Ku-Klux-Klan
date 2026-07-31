# repair_manager.py
# Krishna Omega Ultra V9.1.1 — Reparación de posiciones

from datetime import datetime
from src.position_manager import Position
from src.trailing_engine import TrailingEngine
from src.logger import get_logger

logger = get_logger(__name__)

def repair_orders(exchange, open_positions):
    """
    Reconstruye posiciones desde el exchange.
    Maneja casos donde TP/SL pueden estar vacíos.
    """
    positions_data = exchange.get_positions()
    if not positions_data:
        logger.info("No hay posiciones activas en el exchange.")
        return

    existing_symbols = {p.symbol for p in open_positions if not p.closed}

    for p in positions_data:
        symbol = p["instId"].replace("-USDT-SWAP", "")
        if symbol in existing_symbols:
            continue

        pos_side = p["posSide"]
        size = float(p["pos"])
        if size == 0:
            continue

        entry_price = float(p["avgPx"])
        pos_id = p["posId"]

        logger.warning(f"Reconstruyendo posición swap: {symbol} {pos_side} size={size}")

        pos = Position(
            symbol=symbol,
            side=pos_side,
            entry=entry_price,
            size=size,
            tp=0.0,
            sl=0.0,
            open_time=datetime.utcnow(),
            ord_id=None,
            sl_algo_id=None,
            tp_algo_id=None,
            pos_id=pos_id,
        )
        pos.closed = False

        # Obtener TP/SL pendientes desde el exchange
        algo_orders = exchange.get_algo_orders(inst_id=p["instId"])
        for algo in algo_orders:
            sl_px = algo.get("slTriggerPx", "")
            tp_px = algo.get("tpTriggerPx", "")
            if sl_px and sl_px != "":
                try:
                    pos.sl = float(sl_px)
                    pos.sl_algo_id = algo["algoId"]
                except ValueError:
                    logger.warning(f"SL inválido: {sl_px}")
            if tp_px and tp_px != "":
                try:
                    pos.tp = float(tp_px)
                    pos.tp_algo_id = algo["algoId"]
                except ValueError:
                    logger.warning(f"TP inválido: {tp_px}")

        # Si no hay TP/SL, calcular valores por defecto
        if pos.tp == 0.0 or pos.sl == 0.0:
            df5 = exchange.fetch_candles(symbol, "5m", 60)
            if df5 is not None and len(df5) > 20:
                from src.indicators import atr
                atr_val = atr(df5, 12).iloc[-1]
                if pos.side == "long":
                    pos.tp = entry_price + atr_val * 2.5 if pos.tp == 0.0 else pos.tp
                    pos.sl = entry_price - atr_val * 1.2 if pos.sl == 0.0 else pos.sl
                else:
                    pos.tp = entry_price - atr_val * 2.5 if pos.tp == 0.0 else pos.tp
                    pos.sl = entry_price + atr_val * 1.2 if pos.sl == 0.0 else pos.sl

        pos.trailing = TrailingEngine(entry_price, pos.open_time, symbol, pos_side)
        pos.trailing.tp = pos.tp
        pos.trailing.sl = pos.sl

        open_positions.append(pos)
        logger.info(f"Posición reconstruida: {symbol} {pos_side} entry={entry_price} size={size}")

    for pos in open_positions:
        if pos.trailing is None:
            pos.trailing = TrailingEngine(pos.entry, pos.open_time, pos.symbol, pos.side)
        pos.trailing.tp = pos.tp
        pos.trailing.sl = pos.sl

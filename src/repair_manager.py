"""
Archivo: src/repair_manager.py
Proyecto: Krishna Omega Ultra
Descripción: Reconstrucción de posiciones con TrailingEngine.
"""
from datetime import datetime
from src.config import *
from src.position_manager import Position
from src.trailing_engine import TrailingEngine
from src.logger import get_logger

logger = get_logger(__name__)

def repair_orders(exchange, open_positions_local):
    exchange_positions = exchange.get_positions(mode='swap')
    local_pos_ids = {p.pos_id for p in open_positions_local if p.pos_id}

    for ep in exchange_positions:
        if float(ep.get('pos', 0)) == 0:
            continue
        sym = ep['instId'].replace('-USDT-SWAP', '')
        side = ep['posSide']
        pos_id = ep['posId']
        if pos_id in local_pos_ids:
            continue
        entry_price = float(ep['avgPx'])
        size = float(ep['pos'])
        logger.warning(f"Reconstruyendo posición swap: {sym} {side} size={size}")
        algo_orders = exchange.get_algo_orders(inst_id=ep['instId'])
        sl_algo_id = tp_algo_id = None
        sl_price = tp_price = 0.0
        for ao in algo_orders:
            if ao.get('slTriggerPx') and ao.get('slTriggerPx') != '0':
                sl_algo_id = ao['algoId']
                sl_price = float(ao['slTriggerPx'])
            if ao.get('tpTriggerPx') and ao.get('tpTriggerPx') != '0':
                tp_algo_id = ao['algoId']
                tp_price = float(ao['tpTriggerPx'])
        pos = Position(sym, side, entry_price, size, tp_price, sl_price, datetime.utcnow(),
                       ord_id=None, sl_algo_id=sl_algo_id, tp_algo_id=tp_algo_id, pos_id=pos_id)
        pos.trailing = TrailingEngine(entry_price, datetime.utcnow(), sym, side)
        if sl_price > 0:
            pos.trailing.current_sl = sl_price
        if tp_price > 0:
            pos.trailing.current_tp_trail_active = True
            pos.trailing.current_tp_sl = tp_price
        open_positions_local.append(pos)

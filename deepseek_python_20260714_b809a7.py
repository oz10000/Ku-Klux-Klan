"""
Archivo: src/repair_manager.py
Proyecto: Krishna Omega Ultra
Descripción: Reconstrucción segura de posiciones desde exchange. No cierra automáticamente.
"""
from datetime import datetime
from src.config import *
from src.position_manager import Position
from src.logger import get_logger

logger = get_logger(__name__)

def repair_orders(exchange, open_positions_local):
    exchange_positions = exchange.get_positions()
    local_pos_ids = {p.pos_id for p in open_positions_local if p.pos_id}

    for ep in exchange_positions:
        inst_id = ep.get('instId', '')
        if not inst_id.endswith('-USDT-SWAP'):
            continue
        sym = inst_id.replace('-USDT-SWAP', '')
        pos_side = ep['posSide']
        pos_id = ep['posId']
        if pos_id in local_pos_ids:
            continue

        entry_price = float(ep['avgPx'])
        size = float(ep['pos'])
        logger.warning(f"Reconstruyendo posición huérfana: {sym} {pos_side} {size} @ {entry_price}")

        # Buscar algos asociados
        algo_orders = exchange.get_algo_orders(inst_id)
        sl_algo_id = tp_algo_id = None
        sl_price = tp_price = 0.0
        for algo in algo_orders:
            if algo.get('instId') != inst_id or algo.get('posSide') != pos_side:
                continue
            if algo.get('slTriggerPx') and algo.get('slTriggerPx') != '0':
                sl_algo_id = algo['algoId']
                sl_price = float(algo['slTriggerPx'])
            if algo.get('tpTriggerPx') and algo.get('tpTriggerPx') != '0':
                tp_algo_id = algo['algoId']
                tp_price = float(algo['tpTriggerPx'])

        pos = Position(sym, pos_side, entry_price, size, tp_price, sl_price,
                       datetime.utcnow(), ord_id=None,
                       sl_algo_id=sl_algo_id, tp_algo_id=tp_algo_id, pos_id=pos_id)
        open_positions_local.append(pos)
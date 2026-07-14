"""
Archivo: src/capital_checker.py
Proyecto: Krishna Omega Ultra
Descripción: Análisis de requisitos de capital por activo.
"""
from src.config import *
from src.exchange_okx import OKXClient
from src.logger import get_logger

logger = get_logger(__name__)

def print_capital_requirements(exchange, balance, leverage):
    print("\n📊 REQUISITOS DE CAPITAL POR ACTIVO (Balance: {} USDT, Apalancamiento: {}x)".format(balance, leverage))
    header = "{:<6} {:<10} {:<8} {:<8} {:<8} {:<12} {:<10} {:<10}".format(
        'Activo', 'Precio', 'minSz', 'lotSz', 'ctVal', 'Min Capital', 'Futures', 'Spot')
    print(header)
    print("-" * len(header))
    for sym in UNIVERSO:
        swap_info = exchange.get_instrument_info(sym)
        if not swap_info:
            continue
        price = exchange.get_mark_price(sym) or 0
        min_sz = swap_info['minSz']
        ct_val = swap_info.get('ctVal', 1)
        lot_sz = swap_info['lotSz']
        min_capital_swap = (min_sz * ct_val) / leverage if min_sz and ct_val else float('inf')
        can_swap = balance >= min_capital_swap
        can_spot = False
        # Spot info no se usa en esta versión, se deja placeholder
        print("{:<6} {:<10.4f} {:<8} {:<8} {:<8} {:<12.2f} {:<10} {:<10}".format(
            sym, price, min_sz, lot_sz, ct_val, min_capital_swap,
            '✅' if can_swap else '❌', '✅' if can_spot else '❌'))
    print("-" * len(header))

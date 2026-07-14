"""
Archivo: tests/test_position_manager.py
Proyecto: Krishna Omega Ultra
Descripción: Pruebas unitarias completas del Position Manager y del flujo de eventos.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd, numpy as np
from datetime import datetime, timedelta
from src.config import *
from src.position_manager import Position, PositionStore

def fake_candle(c, h=None, l=None):
    return {'c':c, 'h':h or c, 'l':l or c}

def fake_df_with_atr(close_series):
    df = pd.DataFrame({
        'h': close_series, 'l': close_series - 0.01,
        'c': close_series, 'o': close_series - 0.005,
        'vol': [1]*len(close_series)
    })
    return df

class MockExchange:
    def __init__(self):
        self.amend_calls = []
    def amend_algo_order(self, inst_id, algo_id, new_sl=None, new_tp=None):
        self.amend_calls.append((inst_id, algo_id, new_sl))

def test_break_even():
    pos = Position("BTC", "long", 100, 1, 110, 90, datetime.utcnow()-timedelta(minutes=20))
    candle = fake_candle(101)
    df = fake_df_with_atr(np.array([100]*200))
    event = pos.update(candle, df)
    assert pos.be_activated
    assert pos.sl == 100.25
    assert event['action'] == 'MODIFY_SL'

def test_trailing_tp_activation():
    pos = Position("ETH", "long", 2000, 1, 2200, 1800, datetime.utcnow())
    candle = fake_candle(2205, h=2205)
    df = fake_df_with_atr(np.array([2000]*200))
    event = pos.update(candle, df)
    assert pos.tp_trail_activated
    assert abs(pos.sl - 2204.9965) < 0.0001
    assert event['action'] == 'MODIFY_SL'

def test_sl_not_moved_backwards():
    pos = Position("SOL", "long", 50, 10, 60, 40, datetime.utcnow())
    pos.tp_trail_activated = True
    pos.sl = 55
    candle = fake_candle(54, h=56, l=53)
    df = fake_df_with_atr(np.array([50]*200))
    event = pos.update(candle, df)
    assert pos.sl == 55
    assert event is None

def test_timeout():
    pos = Position("ADA", "long", 1, 1000, 1.5, 0.8, datetime.utcnow()-timedelta(minutes=76))
    candle = fake_candle(1.2)
    df = fake_df_with_atr(np.array([1]*200))
    event = pos.update(candle, df)
    assert pos.closed
    assert event['action'] == 'CLOSE'

def test_full_trailing_execution():
    """Simula el flujo real: Position genera MODIFY_SL y el bot (mock) lo aplica."""
    pos = Position("BTC", "long", 60000, 0.001, 61320, 59000, datetime.utcnow(),
                   sl_algo_id='sl123')
    candle = fake_candle(61500, h=61600, l=61400)
    df = fake_df_with_atr(np.array([60000]*200))
    event = pos.update(candle, df)
    assert event['action'] == 'MODIFY_SL'
    mock_ex = MockExchange()
    # Simulación del handle del bot
    mock_ex.amend_algo_order("BTC-USDT-SWAP", event['algo_id'], new_sl=event['new_sl'])
    assert len(mock_ex.amend_calls) == 1

if __name__ == '__main__':
    test_break_even()
    test_trailing_tp_activation()
    test_sl_not_moved_backwards()
    test_timeout()
    test_full_trailing_execution()
    print("✅ Todas las pruebas pasaron")
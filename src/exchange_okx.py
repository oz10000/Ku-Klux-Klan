"""
Archivo: src/exchange_okx.py
Proyecto: Krishna Omega Ultra
Descripción: Cliente OKX usando la librería oficial okx (v1.0.5+).
Wrapper que proporciona los métodos necesarios para el bot.
"""
import time
import pandas as pd
from datetime import datetime
from okx.Account import AccountAPI
from okx.Market import MarketAPI
from okx.Trade import TradeAPI
from okx.PublicData import PublicAPI
from src.config import *
from src.logger import get_logger

logger = get_logger(__name__)

class OKXClient:
    def __init__(self):
        # Configurar flags para demo
        flag = '1' if OKX_DEMO else '0'  # 1: demo, 0: real
        self.account = AccountAPI(OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE, flag=flag)
        self.market = MarketAPI(OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE, flag=flag)
        self.trade = TradeAPI(OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE, flag=flag)
        self.public = PublicAPI(OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE, flag=flag)

    def _inst_id(self, symbol):
        return f"{symbol}-USDT-SWAP"

    def fetch_candles(self, symbol, bar='5m', limit=200):
        """Obtiene velas históricas usando el endpoint público de OKX."""
        try:
            resp = self.market.get_candlesticks(self._inst_id(symbol), bar=bar, limit=limit)
            data = resp.get('data', [])
            if not data:
                return None
            rows = []
            for d in reversed(data):
                ts = datetime.fromtimestamp(int(d[0]) / 1000)
                rows.append([ts, float(d[1]), float(d[2]), float(d[3]), float(d[4]), float(d[5])])
            return pd.DataFrame(rows, columns=['ts', 'o', 'h', 'l', 'c', 'vol'])
        except Exception as e:
            logger.error(f"Error al obtener velas para {symbol}: {e}")
            return None

    def get_positions(self):
        """Obtiene todas las posiciones abiertas en SWAP."""
        try:
            resp = self.account.get_positions(instType='SWAP')
            return resp.get('data', [])
        except Exception as e:
            logger.error(f"Error al obtener posiciones: {e}")
            return []

    def place_market_order(self, sym, side, sz):
        """Envía orden de mercado. side: 'buy' o 'sell'."""
        try:
            resp = self.trade.place_order(
                instId=self._inst_id(sym),
                tdMode='isolated',
                side=side,
                ordType='market',
                sz=str(sz)
            )
            return resp
        except Exception as e:
            logger.error(f"Error en orden de mercado {sym}: {e}")
            return {'code': '-1', 'msg': str(e)}

    def create_algo_order(self, sym, pos_side, size, tp_price=None, sl_price=None):
        """Crea una orden trigger (TP/SL) para cerrar posición."""
        if not tp_price and not sl_price:
            return None
        body = {
            'instId': self._inst_id(sym),
            'tdMode': 'isolated',
            'side': 'buy' if pos_side == 'long' else 'sell',
            'posSide': pos_side,
            'ordType': 'trigger',
            'sz': str(size)
        }
        if tp_price:
            body['tpTriggerPx'] = str(tp_price)
            body['tpOrdPx'] = str(tp_price)
        if sl_price:
            body['slTriggerPx'] = str(sl_price)
            body['slOrdPx'] = str(sl_price)
        try:
            resp = self.trade.place_algo_order(**body)
            return resp
        except Exception as e:
            logger.error(f"Error al crear orden TP/SL para {sym}: {e}")
            return {'code': '-1', 'msg': str(e)}

    def get_algo_orders(self, inst_id=None, algo_ids=None):
        """Obtiene órdenes algo pendientes, opcionalmente filtradas."""
        try:
            params = {'instType': 'SWAP'}
            if inst_id:
                params['instId'] = inst_id
            resp = self.trade.get_algo_order_list(**params)
            orders = resp.get('data', [])
            if algo_ids:
                orders = [o for o in orders if o.get('algoId') in algo_ids]
            return orders
        except Exception as e:
            logger.error(f"Error al obtener órdenes algo: {e}")
            return []

    def amend_algo_order(self, inst_id, algo_id, new_sl=None, new_tp=None):
        """Modifica el trigger price de una orden algo existente."""
        body = {'instId': inst_id, 'algoId': algo_id}
        if new_sl is not None:
            body['newSlTriggerPx'] = str(new_sl)
        if new_tp is not None:
            body['newTpTriggerPx'] = str(new_tp)
        try:
            resp = self.trade.amend_algo_order(**body)
            return resp
        except Exception as e:
            logger.error(f"Error al modificar orden algo {algo_id}: {e}")
            return {'code': '-1', 'msg': str(e)}

    def close_position(self, sym, pos_id):
        """Cierra manualmente una posición específica."""
        try:
            resp = self.trade.close_position(
                instId=self._inst_id(sym),
                posId=pos_id,
                mgnMode='isolated'
            )
            return resp
        except Exception as e:
            logger.error(f"Error al cerrar posición {sym}: {e}")
            return {'code': '-1', 'msg': str(e)}

    def get_balance(self, ccy='USDT'):
        """Obtiene el saldo disponible en una moneda."""
        try:
            resp = self.account.get_account_balance(ccy=ccy)
            details = resp.get('data', [{}])[0].get('details', [])
            for d in details:
                if d['ccy'] == ccy:
                    return float(d['availBal'])
            return 0.0
        except Exception as e:
            logger.error(f"Error al obtener balance: {e}")
            return 0.0

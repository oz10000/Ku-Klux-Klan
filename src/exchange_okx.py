"""
Archivo: src/exchange_okx.py
Proyecto: Krishna Omega Ultra
Descripción: Cliente OKX usando la librería oficial okx. Si falla la importación,
usa una implementación manual con sincronización horaria (server time OKX).
"""
import time
import json
import requests
import pandas as pd
from datetime import datetime
from src.config import *
from src.logger import get_logger

logger = get_logger(__name__)

# Intentamos usar la librería oficial (más segura)
try:
    from okx.Account import AccountAPI
    from okx.Market import MarketAPI
    from okx.Trade import TradeAPI
    OFFICIAL_LIB = True
except ImportError:
    OFFICIAL_LIB = False
    logger.warning("Librería okx no encontrada. Usando implementación manual con sincronización horaria.")


class OKXClient:
    def __init__(self):
        self.api_key = OKX_API_KEY
        self.secret = OKX_SECRET_KEY
        self.passphrase = OKX_PASSPHRASE
        self.base_url = "https://www.okx.com"
        self.demo = OKX_DEMO
        if OFFICIAL_LIB:
            flag = '1' if self.demo else '0'
            self.account = AccountAPI(self.api_key, self.secret, self.passphrase, flag=flag)
            self.market = MarketAPI(self.api_key, self.secret, self.passphrase, flag=flag)
            self.trade = TradeAPI(self.api_key, self.secret, self.passphrase, flag=flag)
        else:
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': 'KrishnaOmega/2.0'})
            self._server_time_offset = 0.0
            self._sync_time()

    def _inst_id(self, symbol):
        return f"{symbol}-USDT-SWAP"

    # ---- Métodos compartidos (usando librería oficial si está disponible) ----
    def fetch_candles(self, symbol, bar='5m', limit=200):
        if OFFICIAL_LIB:
            try:
                resp = self.market.get_candlesticks(self._inst_id(symbol), bar=bar, limit=limit)
                data = resp.get('data', [])
            except Exception as e:
                logger.error(f"Error fetch candles oficial: {e}")
                return None
        else:
            data = self._manual_fetch_candles(symbol, bar, limit)
        if not data:
            return None
        rows = []
        for d in reversed(data):
            ts = datetime.fromtimestamp(int(d[0]) / 1000)
            rows.append([ts, float(d[1]), float(d[2]), float(d[3]), float(d[4]), float(d[5])])
        return pd.DataFrame(rows, columns=['ts', 'o', 'h', 'l', 'c', 'vol'])

    def get_positions(self):
        if OFFICIAL_LIB:
            try:
                resp = self.account.get_positions(instType='SWAP')
                return resp.get('data', [])
            except Exception as e:
                logger.error(f"Error get_positions oficial: {e}")
                return []
        else:
            return self._manual_request('GET', '/api/v5/account/positions', params={'instType': 'SWAP'}).get('data', [])

    def place_market_order(self, sym, side, sz):
        body = {'instId': self._inst_id(sym), 'tdMode': 'isolated', 'side': side, 'ordType': 'market', 'sz': str(sz)}
        if OFFICIAL_LIB:
            try:
                return self.trade.place_order(**body)
            except Exception as e:
                logger.error(f"Error place_order oficial: {e}")
                return {'code': '-1', 'msg': str(e)}
        else:
            return self._manual_request('POST', '/api/v5/trade/order', body=body)

    def create_algo_order(self, sym, pos_side, size, tp_price=None, sl_price=None):
        if not tp_price and not sl_price:
            return None
        body = {
            'instId': self._inst_id(sym), 'tdMode': 'isolated',
            'side': 'buy' if pos_side == 'long' else 'sell',
            'posSide': pos_side, 'ordType': 'trigger', 'sz': str(size)
        }
        if tp_price:
            body['tpTriggerPx'] = str(tp_price); body['tpOrdPx'] = str(tp_price)
        if sl_price:
            body['slTriggerPx'] = str(sl_price); body['slOrdPx'] = str(sl_price)
        if OFFICIAL_LIB:
            try:
                return self.trade.place_algo_order(**body)
            except Exception as e:
                logger.error(f"Error create_algo oficial: {e}")
                return {'code': '-1', 'msg': str(e)}
        else:
            return self._manual_request('POST', '/api/v5/trade/order-algo', body=body)

    def get_algo_orders(self, inst_id=None, algo_ids=None):
        params = {'instType': 'SWAP'}
        if inst_id:
            params['instId'] = inst_id
        if OFFICIAL_LIB:
            try:
                resp = self.trade.get_algo_order_list(**params)
                orders = resp.get('data', [])
            except Exception as e:
                logger.error(f"Error get_algo oficial: {e}")
                return []
        else:
            orders = self._manual_request('GET', '/api/v5/trade/orders-algo-pending', params=params).get('data', [])
        if algo_ids:
            orders = [o for o in orders if o.get('algoId') in algo_ids]
        return orders

    def amend_algo_order(self, inst_id, algo_id, new_sl=None, new_tp=None):
        body = {'instId': inst_id, 'algoId': algo_id}
        if new_sl is not None: body['newSlTriggerPx'] = str(new_sl)
        if new_tp is not None: body['newTpTriggerPx'] = str(new_tp)
        if OFFICIAL_LIB:
            try:
                return self.trade.amend_algo_order(**body)
            except Exception as e:
                logger.error(f"Error amend_algo oficial: {e}")
                return {'code': '-1', 'msg': str(e)}
        else:
            return self._manual_request('POST', '/api/v5/trade/amend-algos', body=body)

    def close_position(self, sym, pos_id):
        body = {'instId': self._inst_id(sym), 'posId': pos_id, 'mgnMode': 'isolated'}
        if OFFICIAL_LIB:
            try:
                return self.trade.close_position(**body)
            except Exception as e:
                logger.error(f"Error close_position oficial: {e}")
                return {'code': '-1', 'msg': str(e)}
        else:
            return self._manual_request('POST', '/api/v5/trade/close-position', body=body)

    def get_balance(self, ccy='USDT'):
        if OFFICIAL_LIB:
            try:
                resp = self.account.get_account_balance(ccy=ccy)
                details = resp.get('data', [{}])[0].get('details', [])
                for d in details:
                    if d['ccy'] == ccy:
                        return float(d['availBal'])
                return 0.0
            except Exception as e:
                logger.error(f"Error balance oficial: {e}")
                return 0.0
        else:
            resp = self._manual_request('GET', '/api/v5/account/balance', params={'ccy': ccy})
            details = resp.get('data', [{}])[0].get('details', [])
            for d in details:
                if d['ccy'] == ccy:
                    return float(d['availBal'])
            return 0.0

    # ---- Implementación manual (fallback) con sincronización horaria ----
    def _sync_time(self):
        """Obtiene el tiempo del servidor OKX y calcula el offset."""
        try:
            resp = requests.get("https://www.okx.com/api/v5/public/time")
            server_ts = float(resp.json()['data'][0]['ts']) / 1000.0
            self._server_time_offset = server_ts - time.time()
            logger.info(f"Sincronización horaria: offset {self._server_time_offset:.3f}s")
        except:
            self._server_time_offset = 0.0

    def _current_ts(self):
        return str(int((time.time() + self._server_time_offset) * 1000))

    def _manual_sign(self, ts, method, path, body=''):
        import base64, hmac
        message = f'{ts}{method}{path}{body}'
        return base64.b64encode(hmac.new(self.secret.encode(), message.encode(), 'sha256').digest()).decode()

    def _manual_request(self, method, path, params=None, body=None, retries=3):
        import urllib.parse
        ts = self._current_ts()
        body_str = json.dumps(body) if body else ''
        request_path = path
        if params:
            query = urllib.parse.urlencode(sorted(params.items()))
            request_path += '?' + query
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': self._manual_sign(ts, method, request_path, body_str),
            'OK-ACCESS-TIMESTAMP': ts,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json',
        }
        if self.demo:
            headers['x-simulated-trading'] = '1'
        url = self.base_url + request_path
        for attempt in range(retries):
            try:
                resp = self.session.request(method, url, data=body_str, headers=headers)
                if resp.status_code == 429:
                    time.sleep(int(resp.headers.get('Retry-After', 5)))
                    continue
                data = resp.json()
                if data.get('code') != '0':
                    logger.error(f"Manual API error {data.get('code')}: {data.get('msg')} (path: {request_path})")
                    if attempt < retries-1:
                        time.sleep(2 ** attempt)
                        continue
                return data
            except Exception as e:
                logger.error(f"Manual request exception: {e}")
                time.sleep(2 ** attempt)
        return {'code': '-1', 'msg': 'Manual retries exhausted'}

    def _manual_fetch_candles(self, symbol, bar, limit):
        resp = self._manual_request('GET', '/api/v5/market/candles',
                                     params={'instId': self._inst_id(symbol), 'bar': bar, 'limit': limit})
        return resp.get('data', [])

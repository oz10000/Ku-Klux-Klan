"""
Archivo: src/exchange_okx.py
Proyecto: Krishna Omega Ultra
Descripción: Cliente OKX API v5 con autenticación, firma corregida (query string),
creación explícita de órdenes TP/SL, reintentos y logs. Soporta amend de stops.
"""
import time, hmac, base64, json, requests, urllib.parse
from datetime import datetime
import pandas as pd
from src.config import *
from src.logger import get_logger

logger = get_logger(__name__)

class OKXClient:
    def __init__(self):
        self.api_key = OKX_API_KEY
        self.secret = OKX_SECRET_KEY
        self.passphrase = OKX_PASSPHRASE
        self.base_url = "https://www.okx.com"
        self.demo = OKX_DEMO
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'KrishnaOmega/2.0'})

    def _sign(self, ts, method, request_path, body=''):
        msg = f'{ts}{method}{request_path}{body}'
        return base64.b64encode(hmac.new(self.secret.encode(), msg.encode(), 'sha256').digest()).decode()

    def _request(self, method, path, params=None, body=None, retries=3, backoff=2):
        ts = str(int(time.time()))
        body_str = json.dumps(body) if body else ''
        request_path = path
        if params:
            query = urllib.parse.urlencode(sorted(params.items()))
            request_path += '?' + query

        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': self._sign(ts, method, request_path, body_str),
            'OK-ACCESS-TIMESTAMP': ts,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json',
        }
        if self.demo:
            headers['x-simulated-trading'] = '1'

        url = self.base_url + request_path
        for attempt in range(retries):
            try:
                resp = self.session.request(method, url, params=None, data=body_str, headers=headers)
                if resp.status_code == 429:
                    sleep_time = int(resp.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limit, durmiendo {sleep_time}s")
                    time.sleep(sleep_time)
                    continue
                data = resp.json()
                if data.get('code') != '0':
                    logger.error(f"API error {data.get('code')}: {data.get('msg')} (path: {request_path})")
                    if attempt < retries-1:
                        time.sleep(backoff ** attempt)
                        continue
                return data
            except Exception as e:
                logger.error(f"Request exception: {e}, attempt {attempt+1}")
                time.sleep(backoff ** attempt)
        return {'code': '-1', 'msg': 'All retries failed'}

    def fetch_candles(self, symbol, bar='5m', limit=200):
        resp = self._request('GET', '/api/v5/market/candles',
                             params={'instId':f'{symbol}-USDT-SWAP','bar':bar,'limit':limit})
        data = resp.get('data',[])
        if not data: return None
        rows = []
        for d in reversed(data):
            ts = datetime.fromtimestamp(int(d[0])/1000)
            rows.append([ts, float(d[1]), float(d[2]), float(d[3]), float(d[4]), float(d[5])])
        return pd.DataFrame(rows, columns=['ts','o','h','l','c','vol'])

    def get_positions(self):
        return self._request('GET','/api/v5/account/positions', params={'instType':'SWAP'}).get('data', [])

    def place_market_order(self, sym, side, sz):
        body = {
            'instId': f'{sym}-USDT-SWAP',
            'tdMode': 'isolated',
            'side': side,
            'ordType': 'market',
            'sz': str(sz)
        }
        return self._request('POST','/api/v5/trade/order', body=body)

    def create_algo_order(self, sym, pos_side, size, tp_price=None, sl_price=None):
        """Crea una orden trigger (SL y/o TP) para el tamaño exacto de la posición."""
        if not tp_price and not sl_price:
            return None
        body = {
            'instId': f'{sym}-USDT-SWAP',
            'tdMode': 'isolated',
            'side': 'buy' if pos_side == 'long' else 'sell',  # cierre
            'posSide': pos_side,
            'ordType': 'trigger',
            'sz': str(size),  # tamaño real de la posición
        }
        if tp_price:
            body['tpTriggerPx'] = str(tp_price)
            body['tpOrdPx'] = str(tp_price)
        if sl_price:
            body['slTriggerPx'] = str(sl_price)
            body['slOrdPx'] = str(sl_price)
        return self._request('POST','/api/v5/trade/order-algo', body=body)

    def get_algo_orders(self, inst_id=None, algo_ids=None):
        params = {'instType': 'SWAP'}
        if inst_id:
            params['instId'] = inst_id
        resp = self._request('GET', '/api/v5/trade/orders-algo-pending', params=params)
        orders = resp.get('data', [])
        if algo_ids:
            orders = [o for o in orders if o.get('algoId') in algo_ids]
        return orders

    def amend_algo_order(self, inst_id, algo_id, new_sl=None, new_tp=None):
        body = {'instId': inst_id, 'algoId': algo_id}
        if new_sl is not None:
            body['newSlTriggerPx'] = str(new_sl)
        if new_tp is not None:
            body['newTpTriggerPx'] = str(new_tp)
        return self._request('POST', '/api/v5/trade/amend-algos', body=body)

    def close_position(self, sym, pos_id):
        body = {'instId':f'{sym}-USDT-SWAP','posId':pos_id,'mgnMode':'isolated'}
        return self._request('POST','/api/v5/trade/close-position', body=body)

    def get_balance(self, ccy='USDT'):
        resp = self._request('GET','/api/v5/account/balance', params={'ccy':ccy})
        details = resp.get('data',[{}])[0].get('details',[])
        for d in details:
            if d['ccy']==ccy: return float(d['availBal'])
        return 0.0
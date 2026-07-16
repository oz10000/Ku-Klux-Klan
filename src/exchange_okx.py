"""
Archivo: src/exchange_okx.py
Proyecto: Krishna Omega Ultra — Final Certified
Descripción: Cliente OKX API v5 completo, con manejo de errores mejorado,
reintentos inteligentes y correcciones validadas en OKX Demo.
"""
import time
import base64
import hmac
import hashlib
import json
import requests
import urllib.parse
from datetime import datetime, timezone
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
        self._leverage_cache = {}
        self._instrument_cache = {}
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'KrishnaOmega/2.0'})
        self._server_time_offset = 0.0
        self._sync_time()

    # --------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------
    def _swap_id(self, sym):
        return f"{sym}-USDT-SWAP"

    def _spot_id(self, sym):
        return f"{sym}-USDT"

    # --------------------------------------------------------------
    # Sincronización horaria y firma
    # --------------------------------------------------------------
    def _sync_time(self):
        try:
            resp = requests.get(f"{self.base_url}/api/v5/public/time", timeout=10)
            server_ts = float(resp.json()['data'][0]['ts']) / 1000.0
            self._server_time_offset = server_ts - time.time()
            logger.info(f"Sincronización horaria: offset {self._server_time_offset:.3f}s")
        except:
            self._server_time_offset = 0.0

    def _iso_ts(self):
        now = datetime.fromtimestamp(time.time() + self._server_time_offset, tz=timezone.utc)
        return now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def _sign(self, ts_iso, method, path, body=''):
        message = f'{ts_iso}{method}{path}{body}'
        return base64.b64encode(hmac.new(self.secret.encode(), message.encode(), hashlib.sha256).digest()).decode()

    def _request(self, method, path, params=None, body=None, retries=3):
        for attempt in range(retries):
            if attempt > 0:
                self._sync_time()
            ts_iso = self._iso_ts()
            body_str = json.dumps(body) if body else ''
            request_path = path
            if params:
                query = urllib.parse.urlencode(sorted(params.items()))
                request_path += '?' + query
            headers = {
                'OK-ACCESS-KEY': self.api_key,
                'OK-ACCESS-SIGN': self._sign(ts_iso, method, request_path, body_str),
                'OK-ACCESS-TIMESTAMP': ts_iso,
                'OK-ACCESS-PASSPHRASE': self.passphrase,
                'Content-Type': 'application/json',
            }
            if self.demo:
                headers['x-simulated-trading'] = '1'
            url = self.base_url + request_path
            try:
                if method == 'GET':
                    resp = self.session.get(url, headers=headers, timeout=15)
                else:
                    resp = self.session.post(url, headers=headers, data=body_str, timeout=15)
                data = resp.json()
                if data.get('code') != '0':
                    err_data = data.get('data', [{}])[0] if data.get('data') else {}
                    s_code = err_data.get('sCode', '')
                    s_msg = err_data.get('sMsg', '')
                    logger.error(
                        f"API error {data.get('code')}: {data.get('msg')} "
                        f"| sCode={s_code} | sMsg={s_msg} (path: {request_path})"
                    )
                    # Manejar error específico de ordType faltante en orders-algo-pending
                    if ('ordType' in data.get('msg', '').lower() and
                        method == 'GET' and 'orders-algo-pending' in path):
                        if params is None:
                            params = {}
                        params['ordType'] = 'conditional'
                        logger.info("Reintentando con ordType='conditional'")
                        return self._request(method, path, params=params, body=body,
                                             retries=retries - attempt - 1)
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                return data
            except Exception as e:
                logger.error(f"Request exception: {e}")
                time.sleep(2 ** attempt)
        return {'code': '-1', 'msg': 'Retries exhausted'}

    def _public_request(self, method, path, params=None):
        url = self.base_url + path
        if params:
            url += '?' + urllib.parse.urlencode(sorted(params.items()))
        try:
            resp = requests.get(url, timeout=10)
            return resp.json()
        except Exception as e:
            logger.error(f"Public request error: {e}")
            return {}

    # --------------------------------------------------------------
    # Self test
    # --------------------------------------------------------------
    def self_test(self):
        logger.info("🔍 Ejecutando self test...")
        try:
            self._sync_time()
            logger.info("✔ Reloj sincronizado")
        except:
            logger.error("✖ Fallo en sincronización")
            return False
        bal = self.get_balance()
        if bal is None:
            logger.error("✖ No se pudo obtener balance")
            return False
        logger.info(f"✔ Balance: {bal} USDT")
        info = self.get_instrument_info('DOGE')
        if not info:
            logger.error("✖ No se pudo obtener información de DOGE")
            return False
        logger.info("✔ Instrumento DOGE OK")
        if not self.set_leverage('DOGE', LEVERAGE, 'long'):
            logger.error("✖ Fallo al configurar apalancamiento")
            return False
        mark = self.get_mark_price('DOGE')
        if mark is None:
            logger.error("✖ No se pudo obtener precio")
            return False
        body = {
            'instId': self._swap_id('DOGE'),
            'tdMode': 'isolated',
            'side': 'buy',
            'posSide': 'long',
            'ordType': 'limit',
            'px': str(round(mark * 0.001, 4)),
            'sz': str(info['minSz'])
        }
        resp = self._request('POST', '/api/v5/trade/order', body=body)
        if resp.get('code') != '0':
            logger.error(f"✖ Error creando orden de test: {resp.get('msg')}")
            return False
        order_id = resp['data'][0]['ordId']
        cancel_resp = self._request('POST', '/api/v5/trade/cancel-order',
                                    body={'instId': self._swap_id('DOGE'), 'ordId': order_id})
        if cancel_resp.get('code') != '0':
            logger.error(f"✖ Error cancelando orden de test: {cancel_resp.get('msg')}")
            return False
        logger.info("✔ Orden de prueba creada y cancelada")
        logger.info("✅ Self test completado exitosamente")
        return True

    # --------------------------------------------------------------
    # Apalancamiento
    # --------------------------------------------------------------
    def set_leverage(self, symbol, leverage, pos_side):
        cache_key = (symbol, pos_side)
        if cache_key in self._leverage_cache:
            return True
        inst_id = self._swap_id(symbol)
        body = {
            "instId": inst_id,
            "lever": str(leverage),
            "mgnMode": "isolated",
            "posSide": pos_side
        }
        resp = self._request('POST', '/api/v5/account/set-leverage', body=body)
        if resp.get('code') == '0':
            logger.info(f"Apalancamiento {symbol} {pos_side} {leverage}x configurado")
            self._leverage_cache[cache_key] = True
            return True
        else:
            logger.error(f"Error set_leverage: {resp.get('msg')}")
            return False

    # --------------------------------------------------------------
    # Información de instrumentos
    # --------------------------------------------------------------
    def get_instrument_info(self, symbol):
        if symbol not in self._instrument_cache:
            resp = self._public_request('GET', '/api/v5/public/instruments',
                                        params={'instType': 'SWAP', 'instId': self._swap_id(symbol)})
            if resp.get('data'):
                data = resp['data'][0]
                self._instrument_cache[symbol] = {
                    'minSz': float(data.get('minSz', 1)),
                    'lotSz': float(data.get('lotSz', 1)),
                    'tickSz': float(data.get('tickSz', 0.01)),
                    'ctVal': float(data.get('ctVal', 1))
                }
            else:
                return None
        return self._instrument_cache[symbol]

    def get_mark_price(self, symbol):
        resp = self._public_request('GET', '/api/v5/market/ticker', params={'instId': self._swap_id(symbol)})
        if resp.get('data'):
            return float(resp['data'][0]['last'])
        return None

    # --------------------------------------------------------------
    # Balance
    # --------------------------------------------------------------
    def get_balance(self, ccy='USDT'):
        resp = self._request('GET', '/api/v5/account/balance', params={'ccy': ccy})
        details = resp.get('data', [{}])[0].get('details', [])
        for d in details:
            if d['ccy'] == ccy:
                return float(d['availBal'])
        return 0.0

    # --------------------------------------------------------------
    # Órdenes de mercado
    # --------------------------------------------------------------
    def place_market_order(self, symbol, side, size, mode='swap', tp_price=None, sl_price=None, pos_side=None):
        inst_id = self._swap_id(symbol) if mode == 'swap' else self._spot_id(symbol)
        body = {
            'instId': inst_id,
            'side': side,
            'ordType': 'market',
            'sz': str(size)
        }
        if mode == 'swap':
            body['tdMode'] = 'isolated'
            body['posSide'] = pos_side
        else:
            body['tdMode'] = 'cross'
        if tp_price or sl_price:
            attach = []
            if tp_price:
                attach.append({'ordType': 'conditional', 'tpTriggerPx': str(tp_price), 'tpOrdPx': '-1'})
            if sl_price:
                attach.append({'ordType': 'conditional', 'slTriggerPx': str(sl_price), 'slOrdPx': '-1'})
            body['attachAlgoOrds'] = attach
        return self._request('POST', '/api/v5/trade/order', body=body)

    # --------------------------------------------------------------
    # Cierre de posiciones (CORREGIDO)
    # --------------------------------------------------------------
    def close_position(self, symbol, pos_id=None, pos_side=None, size=None, mode='swap'):
        if mode == 'swap':
            if not pos_id or not pos_side:
                logger.error("close_position swap requiere pos_id y pos_side")
                return {'code': '-1'}
            body = {
                'instId': self._swap_id(symbol),
                'posId': pos_id,
                'mgnMode': 'isolated',
                'posSide': pos_side
            }
            resp = self._request('POST', '/api/v5/trade/close-position', body=body)
            # Si la posición ya fue cerrada por TP/SL, consideramos éxito
            if resp.get('code') == '51023':
                logger.warning(f"Posición {pos_id} ya estaba cerrada (51023).")
                return {'code': '0'}
            return resp
        else:
            if size is None:
                logger.error("close_position spot requiere size")
                return {'code': '-1'}
            return self.place_market_order(symbol, 'sell', size, mode='spot')

    # --------------------------------------------------------------
    # Posiciones
    # --------------------------------------------------------------
    def get_positions(self, mode='swap'):
        if mode == 'swap':
            return self._request('GET', '/api/v5/account/positions', params={'instType': 'SWAP'}).get('data', [])
        return []

    # --------------------------------------------------------------
    # Órdenes algorítmicas (TP/SL)
    # --------------------------------------------------------------
    def create_algo_order(self, symbol, pos_side, size, tp_price=None, sl_price=None):
        if not tp_price and not sl_price:
            return None
        inst_id = self._swap_id(symbol)
        close_side = 'sell' if pos_side == 'long' else 'buy'
        body = {
            'instId': inst_id,
            'tdMode': 'isolated',
            'side': close_side,
            'posSide': pos_side,
            'ordType': 'conditional',
            'sz': str(size)
        }
        if tp_price:
            body['tpTriggerPx'] = str(tp_price)
            body['tpOrdPx'] = '-1'
        if sl_price:
            body['slTriggerPx'] = str(sl_price)
            body['slOrdPx'] = '-1'
        return self._request('POST', '/api/v5/trade/order-algo', body=body)

    def get_algo_orders(self, inst_id=None, algo_ids=None):
        params = {'instType': 'SWAP', 'ordType': 'conditional'}
        if inst_id:
            params['instId'] = inst_id
        resp = self._request('GET', '/api/v5/trade/orders-algo-pending', params=params)
        orders = resp.get('data', []) if resp else []
        if algo_ids:
            orders = [o for o in orders if o.get('algoId') in algo_ids]
        return orders

    def amend_algo_order(self, inst_id, algo_id, new_sl=None, new_tp=None):
        body = {'instId': inst_id, 'algoId': algo_id}
        if new_sl is not None:
            body['newSlTriggerPx'] = str(new_sl)
        if new_tp is not None:
            body['newTpTriggerPx'] = str(new_tp)
        for attempt in range(3):
            resp = self._request('POST', '/api/v5/trade/amend-algos', body=body)
            if resp.get('code') == '0':
                return resp
            if resp.get('code') in ('50113', '50102', '50111', '50112'):
                logger.warning(f"Reintentando amend por error de timestamp (intento {attempt+1})")
                self._sync_time()
                continue
            break
        return resp

    # --------------------------------------------------------------
    # Velas históricas
    # --------------------------------------------------------------
    def fetch_candles(self, symbol, bar='5m', limit=200):
        inst_id = self._swap_id(symbol)
        resp = self._request('GET', '/api/v5/market/candles',
                             params={'instId': inst_id, 'bar': bar, 'limit': limit})
        data = resp.get('data', [])
        if not data:
            return None
        rows = []
        for d in reversed(data):
            ts = datetime.fromtimestamp(int(d[0]) / 1000, tz=timezone.utc)
            rows.append([ts, float(d[1]), float(d[2]), float(d[3]), float(d[4]), float(d[5])])
        return pd.DataFrame(rows, columns=['ts', 'o', 'h', 'l', 'c', 'vol'])

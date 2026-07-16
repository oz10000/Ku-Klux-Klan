#!/usr/bin/env python3
"""
Archivo: main_live.py
Proyecto: Krishna Omega Ultra
Descripción: Bot de trading con ejecución continua dentro del timeout de GH Actions.
"""
import time, os, json, subprocess
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
from src.config import *
from src.exchange_okx import OKXClient
from src.strategy_rama_b import StrategyRamaB
from src.position_manager import Position, PositionStore
from src.risk_manager import RiskManager
from src.trailing_engine import TrailingEngine
from src.repair_manager import repair_orders
from src.logger import get_logger
from src.metrics import compute_all, save_report
from src.state_manager import StateManager

logger = get_logger(__name__)

GITHUB_TOKEN = os.getenv("GH_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY", "")
STATE_BRANCH = "state-storage"

def push_state_to_git():
    if not GITHUB_TOKEN or not REPO:
        return False
    try:
        subprocess.run(["git", "config", "user.email", "bot@krishna.omega"], check=True)
        subprocess.run(["git", "config", "user.name", "KrishnaBot"], check=True)
        subprocess.run(["git", "fetch", "origin", STATE_BRANCH], check=False)
        subprocess.run(["git", "checkout", "-b", STATE_BRANCH, f"origin/{STATE_BRANCH}"], check=False)
        subprocess.run(["git", "checkout", STATE_BRANCH], check=False)
        if os.path.exists("state"):
            subprocess.run(["cp", "-r", "state/.", "."], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"state update {datetime.utcnow().isoformat()}"], check=False)
        subprocess.run(["git", "push", "origin", STATE_BRANCH], check=True)
        subprocess.run(["git", "checkout", "-"], check=True)
        return True
    except Exception as e:
        logger.error(f"No se pudo guardar estado en Git: {e}")
        return False

class Dashboard:
    def __init__(self, sm):
        self.sm = sm
        self.start_time = datetime.utcnow()

    def record_trade(self, pnl):
        pass

    def print_summary(self):
        data = self.sm.load_all()
        metrics = data.get('metrics', {})
        trades = data.get('trades', [])
        now = datetime.utcnow()
        print("\n" + "="*60)
        print(f"🐺 KRISHNA OMEGA ULTRA — Dashboard a las {now.strftime('%H:%M:%S')}")
        print("="*60)
        hours = max((now - self.start_time).total_seconds() / 3600, 1)
        pnl_hour = metrics.get('net_pnl', 0) / hours
        trades_hour = len(trades) / hours
        print(f"  PnL/hora: {pnl_hour:.2f} USDT")
        print(f"  Trades/hora: {trades_hour:.2f}")
        print("="*60)

class TradingBot:
    def __init__(self):
        self.ex = OKXClient()
        self.strat = StrategyRamaB(self.ex)
        self.rm = RiskManager(INITIAL_CAPITAL)
        self.store = PositionStore()
        self.sm = StateManager()
        self.open_positions = self.store.load()
        self.running = True
        self.trades = []
        self.equity = [INITIAL_CAPITAL]
        self.dashboard = Dashboard(self.sm)
        self._data_1m = {}
        self.sm.save_positions(self.open_positions)

    def _get_1m_data(self, symbol):
        now = datetime.utcnow()
        key = (symbol, now.replace(second=0, microsecond=0))
        if key not in self._data_1m:
            df1 = self.ex.fetch_candles(symbol, '1m', 60)
            if df1 is not None and len(df1) >= 20:
                self._data_1m[key] = df1
            else:
                time.sleep(1)
                df1 = self.ex.fetch_candles(symbol, '1m', 60)
                self._data_1m[key] = df1 if (df1 is not None and len(df1) >= 20) else None
        return self._data_1m.get(key)

    def handle_event(self, pos, event):
        if pos.closed:          # Evitar doble cierre
            return
        if event is None:
            return
        action = event['action']
        price = event.get('price')
        reason = event.get('reason', '')
        if action in ('MOVE_SL', 'ACTIVATE_TP_TRAIL'):
            if pos.sl_algo_id:
                self.ex.amend_algo_order(f"{pos.symbol}-USDT-SWAP", pos.sl_algo_id, new_sl=price)
                logger.info(f"SL movido a {price:.4f} para {pos.symbol}")
            pos.sl = price
            self.sm.save_trailing_event({
                'time': datetime.utcnow().isoformat(),
                'symbol': pos.symbol,
                'action': action,
                'new_sl': price
            })
            if action == 'ACTIVATE_TP_TRAIL':
                pos.trailing.current_tp_trail_active = True
        elif action == 'CLOSE':
            if pos.pos_id and not pos.closed:
                self.ex.close_position(pos.symbol, pos_id=pos.pos_id, pos_side=pos.side)
            if pos.side == 'long':
                pnl_gross = (price - pos.entry) * pos.size
            else:
                pnl_gross = (pos.entry - price) * pos.size
            comm = pos.size * price * COMMISSION_RATE
            net = pnl_gross - comm
            trade = {
                'symbol': pos.symbol,
                'entry': pos.entry,
                'exit': price,
                'pnl_net': net,
                'reason': reason,
                'hold_minutes': (datetime.utcnow() - pos.entry_time).total_seconds()/60,
                'time': datetime.utcnow().isoformat()
            }
            self.trades.append(trade)
            self.sm.save_trade(trade)
            logger.info(f"Posición cerrada: {pos.symbol} {reason} PnL: {net:.2f}")
            self.dashboard.print_summary()
            pos.closed = True
            pos.exit_price = price
            pos.reason = reason
            self.open_positions.remove(pos)
            self.sm.save_positions(self.open_positions)

    def fetch_data(self):
        d5, d15 = {}, {}
        for sym in UNIVERSO:
            df5 = self.ex.fetch_candles(sym, '5m', 200)
            if df5 is not None and len(df5) >= 60:
                d5[sym] = df5
                idx = df5.set_index('ts')
                df15 = idx['c'].resample('15min', label='right').last().dropna()
                if len(df15) >= 20:
                    d15[sym] = pd.DataFrame({'c': df15})
        return d5, d15

    def place_order_with_retry(self, symbol, side, entry_price, tp, sl, pos_side):
        factor = self.rm.get_factor(symbol)
        logger.info(f"{symbol}: factor inicial {factor:.4f}")
        for attempt in range(MAX_SIZE_RETRIES):
            size = self.rm.calculate_size(entry_price, symbol, self.ex, factor)
            if size <= 0:
                logger.error(f"{symbol}: tamaño inválido con factor {factor:.4f}")
                factor = max(MIN_MARGIN_FACTOR, factor - FACTOR_STEP)
                continue
            info = self.ex.get_instrument_info(symbol)
            margin_required = (size * entry_price) / LEVERAGE if info else 0
            logger.info(f"Intento {attempt+1}: factor={factor:.4f} size={size} margen_req={margin_required:.2f} margen_disp={self.rm.current:.2f}")
            resp = self.ex.place_market_order(symbol, side, size, mode='swap',
                                              tp_price=tp, sl_price=sl, pos_side=pos_side)
            self.sm.save_order({
                'time': datetime.utcnow().isoformat(),
                'symbol': symbol,
                'side': side,
                'size': size,
                'factor': factor,
                'attempt': attempt+1,
                'success': resp.get('code') == '0',
                'response': resp
            })
            if resp.get('code') == '0':
                self.rm.set_factor(symbol, factor)
                self.rm.record_success(symbol)
                return resp, size
            elif resp.get('code') == '1':
                s_code = resp.get('data', [{}])[0].get('sCode', '')
                if s_code == '51008':
                    logger.warning(f"{symbol}: 51008 – reduciendo factor")
                    self.rm.record_failure(symbol)
                    factor = max(MIN_MARGIN_FACTOR, factor - FACTOR_STEP)
                else:
                    logger.error(f"{symbol}: error {s_code}")
                    return None, 0
            else:
                logger.error(f"Error en orden: {resp}")
                return None, 0
        logger.error(f"{symbol}: no se encontró tamaño válido")
        return None, 0

    def run(self):
        logger.info("🚀 KRISHNA OMEGA ULTRA INICIADO")
        if not self.ex.self_test():
            logger.critical("❌ Self test fallido. Bot detenido.")
            return

        repair_orders(self.ex, self.open_positions)
        for pos in self.open_positions:
            if pos.trailing is None:
                pos.trailing = TrailingEngine(pos.entry, pos.entry_time, pos.symbol, pos.side)
        self.sm.save_positions(self.open_positions)

        initial_balance = self.ex.get_balance()
        if initial_balance > 0:
            self.rm.peak = initial_balance
            self.rm.current = initial_balance
            self.rm.initial = initial_balance
            logger.info(f"Capital de referencia ajustado a {initial_balance:.2f} USDT")
        else:
            logger.warning("Balance inicial 0 – kill‑switch desactivado hasta fondos.")

        last_dashboard_time = datetime.utcnow()
        while self.running:
            now = datetime.utcnow()
            # Sin filtro horario; el scoring horario ya gestiona la calidad de la señal

            bal = self.ex.get_balance()
            self.rm.update(bal)
            self.equity.append(bal)

            kill_active = self.rm.check_kill()
            if kill_active:
                logger.warning("Kill switch activo: no se abrirán nuevas posiciones.")
                # Aún podemos cerrar posiciones existentes y actualizar trailing
            else:
                d5, d15 = self.fetch_data()
                self.verify_protection()

                for pos in self.open_positions[:]:
                    if pos.closed: continue
                    symbol = pos.symbol
                    if symbol not in d5: continue
                    df5 = d5[symbol]
                    candle_5m = df5.iloc[-1] if not df5.empty else None
                    if candle_5m is None: continue
                    df1 = self._get_1m_data(symbol)
                    df15 = d15.get(symbol)
                    event = pos.trailing.evaluate(candle_5m, df5, df1, df15)
                    self.handle_event(pos, event)

                if len([p for p in self.open_positions if not p.closed]) < MAX_POSITIONS:
                    sig = self.strat.generate_signal(d5, d15)
                    if sig:
                        self.sm.save_signal(sig)
                        pos_side = 'long' if sig['direction'].lower() == 'long' else 'short'
                        if not self.ex.set_leverage(sig['symbol'], LEVERAGE, pos_side):
                            logger.error(f"No se pudo configurar apalancamiento para {sig['symbol']}. Cancelando.")
                            continue
                        resp, size = self.place_order_with_retry(
                            sig['symbol'],
                            'buy' if sig['direction'] == 'Long' else 'sell',
                            sig['entry'], sig['tp'], sig['sl'], pos_side
                        )
                        if resp is None:
                            continue
                        time.sleep(1)
                        positions = self.ex.get_positions()
                        pos_id = None
                        for p in positions:
                            if p['instId'] == f"{sig['symbol']}-USDT-SWAP" and p['posSide'] == pos_side:
                                pos_id = p['posId']
                                break
                        if not pos_id:
                            time.sleep(2)
                            positions = self.ex.get_positions()
                            for p in positions:
                                if p['instId'] == f"{sig['symbol']}-USDT-SWAP" and p['posSide'] == pos_side:
                                    pos_id = p['posId']
                                    break
                        if not pos_id:
                            logger.error("No se pudo obtener pos_id. Abortando entrada.")
                            continue
                        algo_resp = self.ex.create_algo_order(sig['symbol'], pos_side, size,
                                                              tp_price=sig['tp'], sl_price=sig['sl'])
                        sl_algo_id = tp_algo_id = None
                        if algo_resp and algo_resp.get('code') == '0':
                            for algo in algo_resp['data']:
                                if algo.get('slTriggerPx','0') != '0': sl_algo_id = algo['algoId']
                                if algo.get('tpTriggerPx','0') != '0': tp_algo_id = algo['algoId']
                        else:
                            logger.error("Fallo al crear órdenes TP/SL.")
                        pos = Position(sig['symbol'], sig['direction'].lower(),
                                       sig['entry'], size, sig['tp'], sig['sl'],
                                       datetime.utcnow(), ord_id=None,
                                       sl_algo_id=sl_algo_id, tp_algo_id=tp_algo_id, pos_id=pos_id)
                        pos.trailing = TrailingEngine(sig['entry'], datetime.utcnow(), sig['symbol'], sig['direction'].lower())
                        self.open_positions.append(pos)
                        self.sm.save_positions(self.open_positions)
                        logger.info(f"Nueva posición: {sig['symbol']} {sig['direction']} (sz={size})")

            self.sm.save_positions(self.open_positions)
            push_state_to_git()

            if (now - last_dashboard_time).total_seconds() >= 300:
                self.dashboard.print_summary()
                last_dashboard_time = now

            time.sleep(300)

        metrics = compute_all(self.trades, self.equity, INITIAL_CAPITAL)
        save_report(metrics)
        self.sm.save_metrics(metrics)
        logger.info(f"Métricas finales guardadas: {metrics}")

if __name__ == '__main__':
    bot = TradingBot()
    bot.run()

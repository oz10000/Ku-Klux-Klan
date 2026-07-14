#!/usr/bin/env python3
"""
Archivo: main_live.py
Proyecto: Krishna Omega Ultra
Descripción: Orquestación del bot con corrección de lot size.
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
from src.repair_manager import repair_orders
from src.logger import get_logger
from src.metrics import compute_all, save_report

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
    def __init__(self):
        self.trades = []
        self.start_time = datetime.utcnow()

    def record_trade(self, pnl):
        now = datetime.utcnow()
        self.trades.append({'time': now, 'pnl': pnl})

    def print_summary(self):
        now = datetime.utcnow()
        if not self.trades:
            return
        daily_pnl = defaultdict(float)
        hourly_pnl = defaultdict(float)
        daily_trades = defaultdict(int)
        hourly_trades = defaultdict(int)
        for t in self.trades:
            day_key = t['time'].strftime('%Y-%m-%d')
            hour_key = t['time'].strftime('%Y-%m-%d %H:00')
            daily_pnl[day_key] += t['pnl']
            hourly_pnl[hour_key] += t['pnl']
            daily_trades[day_key] += 1
            hourly_trades[hour_key] += 1

        current_hour = now.strftime('%Y-%m-%d %H:00')
        current_day = now.strftime('%Y-%m-%d')
        pnl_hour = hourly_pnl.get(current_hour, 0.0)
        pnl_day = daily_pnl.get(current_day, 0.0)
        trades_hour = hourly_trades.get(current_hour, 0)
        trades_day = daily_trades.get(current_day, 0)

        hours_since_start = max((now - self.start_time).total_seconds() / 3600, 1)
        avg_pnl_hour = sum(t['pnl'] for t in self.trades) / hours_since_start
        avg_trades_hour = len(self.trades) / hours_since_start

        print("\n" + "="*60)
        print(f"🐺 KRISHNA OMEGA ULTRA — Dashboard a las {now.strftime('%H:%M:%S')}")
        print("="*60)
        print(f"  PnL última hora:  {pnl_hour:>8.2f} USDT")
        print(f"  PnL hoy:          {pnl_day:>8.2f} USDT")
        print(f"  Trades última hora: {trades_hour:>5d}")
        print(f"  Trades hoy:         {trades_day:>5d}")
        print(f"  Promedio PnL/hora:  {avg_pnl_hour:>8.2f} USDT")
        print(f"  Promedio trades/h:  {avg_trades_hour:>5.1f}")
        print("="*60)

class TradingBot:
    def __init__(self):
        self.ex = OKXClient()
        self.strat = StrategyRamaB(self.ex)
        self.rm = RiskManager(INITIAL_CAPITAL)
        self.store = PositionStore()
        self.open_positions = self.store.load()
        self.running = True
        self.trades = []
        self.equity = [INITIAL_CAPITAL]
        self.dashboard = Dashboard()
        self.current_mode = 'swap'   # siempre futuros en esta versión

    def verify_protection(self):
        for pos in self.open_positions:
            if pos.closed: continue
            inst_id = f"{pos.symbol}-USDT-SWAP"
            existing_algos = self.ex.get_algo_orders(inst_id, [pos.sl_algo_id, pos.tp_algo_id])
            sl_found = any(a['algoId'] == pos.sl_algo_id and a.get('slTriggerPx','0') != '0' for a in existing_algos) if pos.sl_algo_id else False
            tp_found = any(a['algoId'] == pos.tp_algo_id and a.get('tpTriggerPx','0') != '0' for a in existing_algos) if pos.tp_algo_id else False
            if not sl_found or not tp_found:
                logger.warning(f"{pos.symbol}: falta protección (SL:{sl_found} TP:{tp_found}). Recreando...")
                self.ex.create_algo_order(pos.symbol, pos.side, pos.size,
                                          tp_price=pos.tp if not tp_found else None,
                                          sl_price=pos.sl if not sl_found else None)
                new_algos = self.ex.get_algo_orders(inst_id)
                for a in new_algos:
                    if a.get('slTriggerPx','0') != '0': pos.sl_algo_id = a['algoId']
                    if a.get('tpTriggerPx','0') != '0': pos.tp_algo_id = a['algoId']
                self.store.save(self.open_positions)

    def handle_position_events(self, pos, event):
        if not event: return
        if event['action'] == 'MODIFY_SL':
            algo_id = event.get('algo_id')
            if algo_id:
                self.ex.amend_algo_order(f"{pos.symbol}-USDT-SWAP", algo_id, new_sl=event['new_sl'])
                logger.info(f"SL modificado: {pos.symbol} → {event['new_sl']}")
            else:
                logger.error(f"No se pudo modificar SL, falta sl_algo_id para {pos.symbol}")
        elif event['action'] == 'CLOSE':
            closed_ok = False
            if pos.pos_id:
                resp = self.ex.close_position(pos.symbol, pos_id=pos.pos_id, pos_side=pos.side)
                if resp.get('code') == '0':
                    for _ in range(5):
                        positions = self.ex.get_positions()
                        if not any(p['posId'] == pos.pos_id for p in positions):
                            closed_ok = True
                            break
                        time.sleep(1)
            if not closed_ok:
                logger.warning(f"No se confirmó cierre de {pos.symbol}.")
                return
            if pos.side == 'long':
                pnl_gross = (event['price'] - pos.entry) * pos.size
            else:
                pnl_gross = (pos.entry - event['price']) * pos.size
            comm = pos.size * event['price'] * COMMISSION_RATE
            net = pnl_gross - comm
            self.trades.append({
                'symbol': pos.symbol, 'entry': pos.entry, 'exit': event['price'],
                'pnl_net': net, 'reason': event.get('reason',''),
                'hold_minutes': (datetime.utcnow() - pos.entry_time).total_seconds()/60
            })
            self.dashboard.record_trade(net)
            logger.info(f"Posición cerrada: {pos.symbol} {event['reason']} PnL: {net:.2f}")
            self.dashboard.print_summary()
            self.open_positions.remove(pos)
            self.store.save(self.open_positions)

    def fetch_data(self):
        d5, d15 = {}, {}
        for sym in UNIVERSO:
            df5 = self.ex.fetch_candles(sym, '5m', 200)
            if df5 is not None and len(df5)>=60:
                d5[sym] = df5
                idx = df5.set_index('ts')
                df15 = idx['c'].resample('15min', label='right').last().dropna()
                if len(df15)>=20:
                    d15[sym] = pd.DataFrame({'c':df15})
        return d5, d15

    def run(self):
        logger.info("🚀 KRISHNA OMEGA ULTRA INICIADO")
        if not self.ex.self_test():
            logger.critical("❌ Self test fallido. Bot detenido.")
            return

        repair_orders(self.ex, self.open_positions)
        self.store.save(self.open_positions)

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
            if now.hour < 14 and now.hour > 0:
                time.sleep(60); continue

            bal = self.ex.get_balance()
            self.rm.update(bal)
            self.equity.append(bal)
            if self.rm.check_kill():
                logger.critical("Kill switch activado. Deteniendo bot.")
                break

            d5, d15 = self.fetch_data()
            self.verify_protection()

            for pos in self.open_positions[:]:
                if pos.closed: continue
                candle = None
                if pos.symbol in d5:
                    df = d5[pos.symbol]
                    if not df.empty: candle = df.iloc[-1]
                if candle is None: continue
                full_df = d5.get(pos.symbol)
                if full_df is None: continue
                event = pos.update(candle, full_df)
                self.handle_position_events(pos, event)

            if len([p for p in self.open_positions if not p.closed]) < MAX_POSITIONS:
                sig = self.strat.generate_signal(d5, d15)
                if sig:
                    pos_side = 'long' if sig['direction'].lower() == 'long' else 'short'
                    if not self.ex.set_leverage(sig['symbol'], LEVERAGE, pos_side):
                        logger.error(f"No se pudo configurar apalancamiento para {sig['symbol']}. Cancelando.")
                        continue
                    sz = self.rm.calculate_size(sig['entry'], sig['symbol'], self.ex)
                    if sz <= 0: continue
                    side = 'buy' if sig['direction'] == 'Long' else 'sell'
                    resp = self.ex.place_market_order(sig['symbol'], side, sz, mode='swap',
                                                      tp_price=sig['tp'], sl_price=sig['sl'], pos_side=pos_side)
                    if resp.get('code') == '0':
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
                        algo_resp = self.ex.create_algo_order(sig['symbol'], pos_side, sz,
                                                              tp_price=sig['tp'], sl_price=sig['sl'])
                        sl_algo_id = tp_algo_id = None
                        if algo_resp and algo_resp.get('code') == '0':
                            for algo in algo_resp['data']:
                                if algo.get('slTriggerPx','0') != '0': sl_algo_id = algo['algoId']
                                if algo.get('tpTriggerPx','0') != '0': tp_algo_id = algo['algoId']
                        else:
                            logger.error("Fallo al crear órdenes TP/SL.")
                        pos = Position(sig['symbol'], sig['direction'].lower(),
                                       sig['entry'], sz, sig['tp'], sig['sl'],
                                       datetime.utcnow(), ord_id=None,
                                       sl_algo_id=sl_algo_id, tp_algo_id=tp_algo_id, pos_id=pos_id)
                        self.open_positions.append(pos)
                        self.store.save(self.open_positions)
                        logger.info(f"Nueva posición: {sig['symbol']} {sig['direction']} (sz={sz})")
                    else:
                        logger.error(f"Error en orden de mercado: {resp}")

            self.store.save(self.open_positions)
            push_state_to_git()

            if (now - last_dashboard_time).total_seconds() >= 300:
                self.dashboard.print_summary()
                last_dashboard_time = now

            next_run = now.replace(second=0, microsecond=0) + timedelta(minutes=5)
            sleep_secs = (next_run - datetime.utcnow()).total_seconds()
            if sleep_secs > 0:
                time.sleep(sleep_secs)

        metrics = compute_all(self.trades, self.equity, INITIAL_CAPITAL)
        save_report(metrics)
        logger.info(f"Métricas finales guardadas: {metrics}")

if __name__ == '__main__':
    bot = TradingBot()
    bot.run()

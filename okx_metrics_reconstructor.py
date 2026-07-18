#!/usr/bin/env python3
"""
okx_metrics_reconstructor.py — Krishna Omega Ultra V9.1.1
Versión para GitHub Actions: lee credenciales de secretos y HOURS de variable de entorno.
"""
import os
import sys
import time
import json
import hmac
import base64
import hashlib
import requests
import urllib.parse
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List

# ------------------------------------------------------------------
# Credenciales desde secretos de GitHub Actions
# ------------------------------------------------------------------
API_KEY    = os.getenv("OKX_API_KEY", "")
SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
BASE_URL   = "https://www.okx.com"
DEMO       = os.getenv("OKX_DEMO", "1") == "1"
MAX_RETRIES = 3
PAGE_SIZE   = 100
COMMISSION_RATE = 0.0008

if not API_KEY or not SECRET_KEY or not PASSPHRASE:
    print("❌ Faltan secretos OKX_API_KEY / OKX_SECRET_KEY / OKX_PASSPHRASE")
    sys.exit(1)

# ------------------------------------------------------------------
# Autenticación (réplica de exchange_okx.py)
# ------------------------------------------------------------------
def sync_time() -> float:
    try:
        resp = requests.get(f"{BASE_URL}/api/v5/public/time", timeout=10)
        server_ts = float(resp.json()["data"][0]["ts"]) / 1000.0
        return server_ts - time.time()
    except:
        return 0.0

def iso_ts(offset: float) -> str:
    now = datetime.fromtimestamp(time.time() + offset, tz=timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def sign(ts_iso: str, method: str, path: str, body: str = "") -> str:
    msg = f"{ts_iso}{method}{path}{body}"
    return base64.b64encode(hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()).decode()

def request(method: str, path: str, params: dict = None, body: dict = None) -> dict:
    offset = sync_time()
    for attempt in range(MAX_RETRIES):
        ts_iso = iso_ts(offset)
        body_str = json.dumps(body) if body else ""
        req_path = path
        if params:
            query = urllib.parse.urlencode(sorted(params.items()))
            req_path += "?" + query
        headers = {
            "OK-ACCESS-KEY": API_KEY,
            "OK-ACCESS-SIGN": sign(ts_iso, method, req_path, body_str),
            "OK-ACCESS-TIMESTAMP": ts_iso,
            "OK-ACCESS-PASSPHRASE": PASSPHRASE,
            "Content-Type": "application/json",
        }
        if DEMO:
            headers["x-simulated-trading"] = "1"
        url = BASE_URL + req_path
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=15)
            else:
                resp = requests.post(url, headers=headers, data=body_str, timeout=15)
            data = resp.json()
            if data.get("code") == "0":
                return data
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 5))
                print(f"  ⏳ Rate limit, esperando {wait}s...")
                time.sleep(wait)
                continue
            print(f"  ⚠️ Error {data.get('code')}: {data.get('msg')}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"  ✖ Excepción: {e}")
            time.sleep(2 ** attempt)
    return {"code": "-1", "msg": "Failed", "data": []}

# ------------------------------------------------------------------
# Descarga paginada
# ------------------------------------------------------------------
def download_history(path: str, begin: str, end: str,
                     extra_params: dict = None, ts_field: str = "ts") -> List[Dict]:
    all_data = []
    params = extra_params.copy() if extra_params else {}
    params["begin"] = begin
    params["end"]   = end
    params["limit"] = PAGE_SIZE

    while True:
        resp = request("GET", path, params=params)
        data = resp.get("data", [])
        if not data:
            break
        all_data.extend(data)
        if len(data) < PAGE_SIZE:
            break
        timestamps = [int(d[ts_field]) for d in data if ts_field in d and d[ts_field]]
        if not timestamps:
            break
        oldest = min(timestamps)
        params["begin"] = str(oldest + 1)
        time.sleep(0.3)

    return all_data

def fetch_fills_history(begin: str, end: str) -> List[Dict]:
    return download_history("/api/v5/trade/fills-history",
                            begin, end, {"instType": "SWAP"}, ts_field="ts")

def fetch_positions_history(begin: str, end: str) -> List[Dict]:
    return download_history("/api/v5/account/positions-history",
                            begin, end, {"instType": "SWAP"}, ts_field="uTime")

def fetch_bills_history(begin: str, end: str) -> List[Dict]:
    return download_history("/api/v5/account/bills-history",
                            begin, end, {}, ts_field="ts")

def fetch_balance() -> float:
    resp = request("GET", "/api/v5/account/balance", params={"ccy": "USDT"})
    details = resp.get("data", [{}])[0].get("details", [])
    for d in details:
        if d["ccy"] == "USDT":
            return float(d["availBal"])
    return 0.0

# ------------------------------------------------------------------
# Reconstrucción de trades
# ------------------------------------------------------------------
def reconstruct_trades(pos_history: List[Dict], fills: List[Dict]) -> List[Dict]:
    fills_by_inst = defaultdict(list)
    for f in fills:
        fills_by_inst[f.get("instId", "")].append(f)

    trades = []
    for pos in pos_history:
        realized_pnl = float(pos.get("realizedPnl", 0))
        if realized_pnl == 0:
            continue
        inst_id = pos.get("instId", "")
        symbol = inst_id.replace("-USDT-SWAP", "")
        side = pos.get("posSide", "net")
        entry_px = float(pos.get("avgPx", 0))
        close_total_pos = float(pos.get("closeTotalPos", 0))
        if close_total_pos == 0:
            continue

        open_time = int(pos.get("cTime", 0))
        close_time = int(pos.get("uTime", 0))
        inst_fills = fills_by_inst.get(inst_id, [])

        entry_fills = [f for f in inst_fills
                       if open_time <= int(f["ts"]) <= close_time
                       and f["side"] == ("buy" if side == "long" else "sell")]
        if entry_fills:
            total_sz = sum(float(f["sz"]) for f in entry_fills)
            if total_sz > 0:
                entry_px = sum(float(f["fillPx"]) * float(f["sz"]) for f in entry_fills) / total_sz

        exit_fills = [f for f in inst_fills
                      if open_time <= int(f["ts"]) <= close_time
                      and f["side"] == ("sell" if side == "long" else "buy")]
        if exit_fills:
            total_sz = sum(float(f["sz"]) for f in exit_fills)
            if total_sz > 0:
                close_px = sum(float(f["fillPx"]) * float(f["sz"]) for f in exit_fills) / total_sz
        else:
            if side == "long":
                close_px = entry_px + realized_pnl / close_total_pos
            else:
                close_px = entry_px - realized_pnl / close_total_pos

        if side == "long":
            pnl_gross = (close_px - entry_px) * close_total_pos
        else:
            pnl_gross = (entry_px - close_px) * close_total_pos

        comm = close_total_pos * close_px * COMMISSION_RATE
        pnl_net = pnl_gross - comm

        hold_minutes = (close_time - open_time) / 60000.0 if open_time and close_time else 0

        trades.append({
            'symbol': symbol,
            'entry': round(entry_px, 6),
            'exit': round(close_px, 6),
            'pnl_net': pnl_net,
            'pnl_gross': pnl_gross,
            'size': close_total_pos,
            'hold_minutes': hold_minutes,
            'time': datetime.fromtimestamp(close_time / 1000, tz=timezone.utc).isoformat()
        })

    trades.sort(key=lambda t: t['time'])
    return trades

# ------------------------------------------------------------------
# Métricas (copia de src/metrics.py)
# ------------------------------------------------------------------
def compute_all(trades: List[Dict], equity_curve: List[float],
                initial_capital: float) -> Dict:
    if not trades:
        return {}
    pnls = [t['pnl_net'] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total = len(pnls)
    win_rate = len(wins)/total*100 if total > 0 else 0
    total_win = sum(wins) if len(wins) > 0 else 0
    total_loss = abs(sum(losses)) if len(losses) > 0 else 1e-9
    profit_factor = total_win / total_loss
    avg_win = sum(wins)/len(wins) if wins else 0
    avg_loss = sum(losses)/len(losses) if losses else 0
    expectancy = sum(pnls)/total if total else 0

    eq = equity_curve if equity_curve else [initial_capital]
    peak = max(eq)
    peak_idx = eq.index(peak)
    dd_values = [(peak - x)/peak*100 for x in eq[peak_idx:]] if peak > 0 else [0]
    max_dd = max(dd_values) if dd_values else 0
    max_dd_dollar = max(peak - x for x in eq) if peak > 0 else 0

    rets = [(eq[i] - eq[i-1]) / eq[i-1] for i in range(1, len(eq)) if eq[i-1] != 0]
    if len(rets) > 1:
        sharpe = (sum(rets)/len(rets)) / (sum((r - sum(rets)/len(rets))**2 for r in rets)/len(rets))**0.5 * (365*24*12)**0.5
    else:
        sharpe = 0
    downside = [r for r in rets if r < 0]
    if len(downside) > 0:
        sortino = (sum(rets)/len(rets)) / (sum((r - sum(rets)/len(rets))**2 for r in downside)/len(downside))**0.5 * (365*24*12)**0.5
    else:
        sortino = float('inf')

    total_days = len(eq) * 5 / (60 * 24)
    cagr = ((eq[-1] / initial_capital) ** (365 / max(1, total_days)) - 1) * 100 if max_dd > 0 else 0
    calmar = cagr / max_dd if max_dd > 0 else 0
    recovery_factor = (eq[-1] - initial_capital) / max_dd_dollar if max_dd_dollar > 0 else 0

    return {
        'trades_total': total,
        'win_rate': round(win_rate, 2),
        'profit_factor': round(profit_factor, 3),
        'net_pnl': round(eq[-1] - initial_capital, 2),
        'final_equity': round(eq[-1], 2),
        'max_drawdown_pct': round(max_dd, 2),
        'max_drawdown_usdt': round(max_dd_dollar, 2),
        'sharpe_ratio': round(sharpe, 3),
        'sortino_ratio': round(sortino, 3),
        'calmar_ratio': round(calmar, 2),
        'cagr': round(cagr, 2),
        'recovery_factor': round(recovery_factor, 2),
        'expectancy': round(expectancy, 3),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'largest_win': round(max(wins), 2) if wins else 0,
        'largest_loss': round(min(losses), 2) if losses else 0,
        'avg_duration_min': round(sum(t['hold_minutes'] for t in trades) / total, 1) if total else 0,
    }

# ------------------------------------------------------------------
# Programa principal
# ------------------------------------------------------------------
def main():
    print("=" * 70)
    print("🔁 KRISHNA OMEGA ULTRA — RECONSTRUCTOR DE MÉTRICAS 1:1")
    print("=" * 70)

    # Leer horas desde variable de entorno (por defecto 5)
    try:
        hours = float(os.getenv("HOURS", "5"))
        if hours <= 0:
            raise ValueError
    except ValueError:
        print("❌ Variable HOURS inválida")
        sys.exit(1)

    now_utc = datetime.now(timezone.utc)
    start_time = now_utc - timedelta(hours=hours)
    begin_ts = str(int(start_time.timestamp() * 1000))
    end_ts   = str(int(now_utc.timestamp() * 1000))

    print(f"\n📅 Período: {start_time.strftime('%Y-%m-%d %H:%M UTC')} → {now_utc.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    print("\n📡 Descargando datos históricos de OKX...")
    fills = fetch_fills_history(begin_ts, end_ts)
    print(f"   Fills: {len(fills)}")
    pos_history = fetch_positions_history(begin_ts, end_ts)
    print(f"   Posiciones cerradas: {len(pos_history)}")
    bills = fetch_bills_history(begin_ts, end_ts)
    print(f"   Bills: {len(bills)}")

    final_balance = fetch_balance()
    total_realized_pnl = sum(float(p.get("realizedPnl", 0)) for p in pos_history)
    funding_net = sum(float(b.get("fee", 0)) for b in bills if b.get("type") == "funding")
    total_commission = sum(float(b.get("fee", 0)) for b in bills if b.get("type") == "trade")

    initial_balance = final_balance - total_realized_pnl - funding_net + total_commission
    if initial_balance <= 0:
        initial_balance = final_balance - total_realized_pnl
        if initial_balance <= 0:
            initial_balance = final_balance + abs(total_realized_pnl)

    print(f"\n💰 Balance final: {final_balance:.2f} USDT")
    print(f"💰 Balance inicial reconstruido: {initial_balance:.2f} USDT")
    print(f"💰 PnL realizado (bruto): {total_realized_pnl:+.2f} USDT")

    trades = reconstruct_trades(pos_history, fills)
    print(f"🔁 Trades reconstruidos: {len(trades)}")

    equity_curve = [initial_balance]
    for t in trades:
        equity_curve.append(equity_curve[-1] + t['pnl_net'])

    metrics = compute_all(trades, equity_curve, initial_balance)

    total_hours = hours
    pnl_per_hour = metrics['net_pnl'] / total_hours if total_hours else 0
    trades_per_hour = len(trades) / total_hours if total_hours else 0

    print("\n" + "=" * 70)
    print("📊 MÉTRICAS RECONSTRUIDAS (1:1 con Krishna Omega Ultra)")
    print("=" * 70)
    print(f"  Balance inicial:             {initial_balance:>10.2f} USDT")
    print(f"  Balance final:               {final_balance:>10.2f} USDT")
    print(f"  PnL neto (realizado):        {metrics['net_pnl']:>+10.2f} USDT")
    print(f"  ROI:                         {metrics['net_pnl']/initial_balance*100:>10.2f}%")
    print(f"  Trades totales:              {metrics['trades_total']:>10d}")
    print(f"  Win Rate:                    {metrics['win_rate']:>10.2f}%")
    print(f"  Profit Factor:               {metrics['profit_factor']:>10.2f}")
    print(f"  Expectancy:                  {metrics['expectancy']:>10.4f} USDT")
    print(f"  Avg Win:                     {metrics['avg_win']:>10.2f} USDT")
    print(f"  Avg Loss:                    {metrics['avg_loss']:>10.2f} USDT")
    print(f"  Largest Win:                 {metrics['largest_win']:>10.2f} USDT")
    print(f"  Largest Loss:                {metrics['largest_loss']:>10.2f} USDT")
    print(f"  Max Drawdown:                {metrics['max_drawdown_pct']:>10.2f}%")
    print(f"  Sharpe Ratio:                {metrics['sharpe_ratio']:>10.3f}")
    print(f"  Sortino Ratio:               {metrics['sortino_ratio']:>10.3f}")
    print(f"  Calmar Ratio:                {metrics['calmar_ratio']:>10.2f}")
    print(f"  CAGR:                        {metrics['cagr']:>10.2f}%")
    print(f"  Recovery Factor:             {metrics['recovery_factor']:>10.2f}")
    print(f"  Duración media trade:        {metrics['avg_duration_min']:>10.1f} min")
    print(f"  PnL / hora:                  {pnl_per_hour:>+10.4f} USDT")
    print(f"  Trades / hora:               {trades_per_hour:>10.2f}")

    by_symbol = defaultdict(list)
    for t in trades:
        by_symbol[t['symbol']].append(t['pnl_net'])
    if by_symbol:
        print("\n📈 MÉTRICAS POR ACTIVO:")
        for sym in sorted(by_symbol):
            pnls = by_symbol[sym]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            pf = sum(wins)/abs(sum(losses)) if losses else float('inf')
            wr = len(wins)/len(pnls)*100 if pnls else 0
            print(f"  {sym:6s}: trades={len(pnls):3d}, WR={wr:.1f}%, PF={pf:.2f}, PnL={sum(pnls):.4f} USDT")

    print("\n✅ Reconstrucción finalizada.")

if __name__ == "__main__":
    main()

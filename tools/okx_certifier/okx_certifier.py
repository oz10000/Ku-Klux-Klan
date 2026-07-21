#!/usr/bin/env python3
"""
okx_certifier.py — Krishna Omega Ultra V9.1.1
Certificador operativo autónomo para OKX Demo (versión corregida).
"""
import os, sys, time, json
from datetime import datetime, timezone
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.config import UNIVERSO, LEVERAGE, OKX_DEMO, INITIAL_CAPITAL
from src.exchange_okx import OKXClient
from src.risk_manager import RiskManager
from src.state_manager import StateManager
from src.metrics import compute_all

MODE = os.getenv("CERTIFIER_MODE", "FULL_CERTIFICATION")
UNIVERSO_EXTRA = ["NEAR", "ATOM", "UNI", "FIL", "ICP", "APT", "ARB", "OP", "TIA", "INJ"]
LOG_FILE = "tools/okx_certifier/okx_certification_report.log"


class OKXCertifier:
    def __init__(self):
        self.ex = OKXClient()
        self.rm = RiskManager(INITIAL_CAPITAL)
        self.sm = StateManager()
        self.report_lines = []
        self.results = {
            "connection": "NOT TESTED",
            "assets": {},
            "long": "NOT TESTED",
            "short": "NOT TESTED",
            "tp": "NOT TESTED",
            "sl": "NOT TESTED",
            "trailing": "NOT TESTED",
            "state": "NOT TESTED",
            "metrics": "NOT TESTED",
            "bot_status": "NOT CERTIFIED",
        }
        self.certified_universe = []
        self.failed_components = []

    def log(self, msg: str):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        self.report_lines.append(line)

    # ─── CONEXIÓN ───────────────────────────────────────────
    def check_connection(self) -> bool:
        self.log("CONNECTION CHECK")
        try:
            self.ex._sync_time()
            self.log("SYNC OK")
            bal = self.ex.get_balance()
            if bal is not None:
                self.log(f"BALANCE OK ({bal:.2f} USDT)")
                self.results["connection"] = "PASS"
                return True
            self.log("BALANCE ERROR")
            self.results["connection"] = "FAIL"
            return False
        except Exception as e:
            self.log(f"CONNECTION FAIL: {e}")
            self.results["connection"] = "FAIL"
            return False

    def check_permissions(self):
        self.log("PERMISSIONS CHECK")
        try:
            self.ex.get_positions()
            self.log("READ PERMISSION OK")
        except:
            self.log("READ PERMISSION WARNING")
        if MODE == "FULL_CERTIFICATION" and OKX_DEMO:
            mark = self.ex.get_mark_price("DOGE")
            if mark:
                resp = self.ex._request("POST", "/api/v5/trade/order", body={
                    "instId": "DOGE-USDT-SWAP", "tdMode": "isolated",
                    "side": "buy", "posSide": "long", "ordType": "limit",
                    "px": str(round(mark * 0.001, 4)), "sz": "1"
                })
                if resp.get("code") == "0":
                    self.ex._request("POST", "/api/v5/trade/cancel-order", body={
                        "instId": "DOGE-USDT-SWAP", "ordId": resp["data"][0]["ordId"]
                    })
                    self.log("WRITE PERMISSION OK")

    # ─── UNIVERSO ───────────────────────────────────────────
    def check_asset(self, sym: str) -> Tuple[str, Dict]:
        info = self.ex.get_instrument_info(sym)
        if not info:
            return "NO DISPONIBLE", {}
        return "PASS", {
            "minSz": info["minSz"], "lotSz": info["lotSz"],
            "tickSz": info["tickSz"], "ctVal": info.get("ctVal", 1)
        }

    def build_universe(self) -> List[str]:
        self.log("UNIVERSE SCAN")
        all_assets = list(UNIVERSO) + UNIVERSO_EXTRA
        working = []
        for sym in all_assets:
            status, specs = self.check_asset(sym)
            self.results["assets"][sym] = status
            if status == "PASS":
                self.log(f"{sym} PASS (minSz={specs['minSz']})")
                working.append(sym)
            else:
                self.log(f"{sym} NO DISPONIBLE (omitido)")
        self.certified_universe = working
        self.log(f"CERTIFIED UNIVERSE: {len(working)} activos")
        return working

    # ─── CAPITAL DEMO ───────────────────────────────────────
    def calculate_required_capital(self, assets: List[str]) -> float:
        max_margin = 0.0
        for sym in assets:
            info = self.ex.get_instrument_info(sym)
            if not info:
                continue
            price = self.ex.get_mark_price(sym) or 1.0
            min_notional = info["minSz"] * info.get("ctVal", 1) * price
            margin = min_notional / LEVERAGE
            if margin > max_margin:
                max_margin = margin
        return round(max_margin * 1.3, 2)

    # ─── VERIFICACIÓN DE TRADE ──────────────────────────────
    def verify_trade_saved(self, sym: str):
        """Espera hasta 3 segundos y comprueba que el trade se haya registrado."""
        for _ in range(6):
            time.sleep(0.5)
            data = self.sm.load_all()
            trades = data.get("trades", [])
            if trades:
                last = trades[-1]
                if last.get("symbol") == sym and last.get("pnl_net") is not None:
                    self.log("  TRADE SAVED OK")
                    eq = [INITIAL_CAPITAL]
                    for t in trades:
                        eq.append(eq[-1] + t.get("pnl_net", 0))
                    m = compute_all(trades, eq, INITIAL_CAPITAL)
                    if m and m.get("win_rate") is not None:
                        self.log(f"  METRICS UPDATED OK (WR={m['win_rate']:.2f}%)")
                        self.results["state"] = "PASS"
                        self.results["metrics"] = "PASS"
                    return
        self.log("  TRADE SAVED WARNING: trade sin pnl o símbolo incorrecto")

    # ─── PRUEBA LONG ────────────────────────────────────────
    def test_long(self, sym: str) -> str:
        if MODE != "FULL_CERTIFICATION":
            return "SKIP"
        # Verificar balance antes de operar
        bal = self.ex.get_balance()
        info = self.ex.get_instrument_info(sym)
        if not info:
            return "NO SPECS"
        size = max(info["minSz"], info["lotSz"])
        price = self.ex.get_mark_price(sym) or 1.0
        required_margin = size * price / LEVERAGE
        if bal < required_margin:
            self.log(f"  SKIP: balance insuficiente ({bal:.2f} < {required_margin:.2f})")
            return "SKIP"

        inst_id = f"{sym}-USDT-SWAP"
        self.log(f"LONG {sym} OPEN (size={size})")
        try:
            resp = self.ex.place_market_order(sym, "buy", size, mode="swap", pos_side="long")
            if resp.get("code") != "0":
                s_code = resp.get("data", [{}])[0].get("sCode", "")
                msg = resp.get("msg", "")
                if s_code == "51087":
                    self.log(f"  DESLISTADO: {sym} será omitido")
                    self.results["assets"][sym] = "DESLISTADO"
                    return "DESLISTADO"
                self.log(f"  OPEN FAIL: {msg}")
                return "FAIL_OPEN"
            self.log("  OPEN OK")
            time.sleep(1.5)

            positions = self.ex.get_positions()
            pos_id = next((p["posId"] for p in positions if p["instId"] == inst_id and p["posSide"] == "long"), None)
            if not pos_id:
                self.log("  POSITION NOT FOUND")
                return "FAIL_POSITION"
            self.log("  POSITION VERIFIED")

            last = self.ex.get_mark_price(sym)
            if not last:
                return "FAIL_PRICE"

            # TP/SL válidos
            tp = round(last * 1.02, 2)
            sl = round(last * 0.98, 2)
            algo_resp = self.ex.create_algo_order(sym, "long", size, tp_price=tp, sl_price=sl)
            if algo_resp and algo_resp.get("code") == "0":
                self.log("  TP/SL CREATED")
                self.results["tp"] = "PASS"
                self.results["sl"] = "PASS"
                algo_id = algo_resp["data"][0]["algoId"]
            else:
                self.log(f"  TP/SL FAIL: {algo_resp.get('msg') if algo_resp else 'None'}")
                algo_id = None

            # Trailing con SL garantizado
            if algo_id:
                new_sl = round(last * 0.99, 2)   # siempre menor que el último precio
                amend_resp = self.ex.amend_algo_order(inst_id, algo_id, new_sl=new_sl)
                if amend_resp.get("code") == "0":
                    time.sleep(0.5)
                    algos = self.ex.get_algo_orders(inst_id, [algo_id])
                    updated = any(
                        a.get("algoId") == algo_id and float(a.get("slTriggerPx", 0)) > sl
                        for a in algos
                    )
                    if updated:
                        self.log("  TRAILING OK")
                        self.results["trailing"] = "PASS"
                    else:
                        self.log("  TRAILING WARNING: no verificado")
                else:
                    self.log(f"  TRAILING FAIL: {amend_resp.get('msg')}")

            # Cierre
            close_resp = self.ex.close_position(sym, pos_id=pos_id, pos_side="long")
            if close_resp.get("code") in ("0", "51023"):
                self.log("  CLOSE OK")
            else:
                self.log(f"  CLOSE FAIL: {close_resp.get('msg')}")
                return "FAIL_CLOSE"

            self.verify_trade_saved(sym)
            return "PASS"
        except Exception as e:
            self.log(f"  ERROR: {e}")
            return "ERROR"

    # ─── PRUEBA SHORT ───────────────────────────────────────
    def test_short(self, sym: str) -> str:
        if MODE != "FULL_CERTIFICATION":
            return "SKIP"
        bal = self.ex.get_balance()
        info = self.ex.get_instrument_info(sym)
        if not info:
            return "NO SPECS"
        size = max(info["minSz"], info["lotSz"])
        price = self.ex.get_mark_price(sym) or 1.0
        required_margin = size * price / LEVERAGE
        if bal < required_margin:
            self.log(f"  SKIP: balance insuficiente")
            return "SKIP"

        inst_id = f"{sym}-USDT-SWAP"
        self.log(f"SHORT {sym} OPEN (size={size})")
        try:
            resp = self.ex.place_market_order(sym, "sell", size, mode="swap", pos_side="short")
            if resp.get("code") != "0":
                s_code = resp.get("data", [{}])[0].get("sCode", "")
                if s_code == "51087":
                    self.log(f"  DESLISTADO: {sym} será omitido")
                    self.results["assets"][sym] = "DESLISTADO"
                    return "DESLISTADO"
                self.log(f"  OPEN FAIL: {resp.get('msg')}")
                return "FAIL_OPEN"
            self.log("  OPEN OK")
            time.sleep(1.5)

            positions = self.ex.get_positions()
            pos_id = next((p["posId"] for p in positions if p["instId"] == inst_id and p["posSide"] == "short"), None)
            if not pos_id:
                self.log("  POSITION NOT FOUND")
                return "FAIL_POSITION"
            self.log("  POSITION VERIFIED")

            last = self.ex.get_mark_price(sym)
            if not last:
                return "FAIL_PRICE"

            tp = round(last * 0.98, 2)
            sl = round(last * 1.02, 2)
            algo_resp = self.ex.create_algo_order(sym, "short", size, tp_price=tp, sl_price=sl)
            if algo_resp and algo_resp.get("code") == "0":
                self.log("  TP/SL CREATED")
                algo_id = algo_resp["data"][0]["algoId"]
            else:
                algo_id = None

            if algo_id:
                new_sl = round(last * 1.01, 2)   # siempre mayor que el último precio
                amend_resp = self.ex.amend_algo_order(inst_id, algo_id, new_sl=new_sl)
                if amend_resp.get("code") == "0":
                    self.log("  TRAILING OK")
                else:
                    self.log(f"  TRAILING FAIL: {amend_resp.get('msg')}")

            close_resp = self.ex.close_position(sym, pos_id=pos_id, pos_side="short")
            if close_resp.get("code") in ("0", "51023"):
                self.log("  CLOSE OK")
            else:
                return "FAIL_CLOSE"

            self.verify_trade_saved(sym)
            return "PASS"
        except Exception as e:
            self.log(f"  ERROR: {e}")
            return "ERROR"

    # ─── EJECUCIÓN PRINCIPAL ────────────────────────────────
    def run(self):
        self.log("=" * 50)
        self.log("KRISHNA OMEGA ULTRA V9.1.1 — OKX CERTIFIER")
        self.log(f"Mode: {MODE} | Time: {datetime.now(timezone.utc).isoformat()}")
        self.log("=" * 50)

        if not self.check_connection():
            self.finalize()
            return

        self.check_permissions()

        if MODE == "FULL_CERTIFICATION":
            working = self.build_universe()
            if not working:
                self.log("NO WORKING ASSETS")
                self.finalize()
                return
            capital_needed = self.calculate_required_capital(working)
            self.log(f"CAPITAL DEMO RECOMENDADO: {capital_needed:.2f} USDT")

            self.log("LONG CERTIFICATION")
            for sym in working:
                result = self.test_long(sym)
                if result == "DESLISTADO":
                    continue
                if result != "PASS":
                    self.results["long"] = "FAIL"
            if self.results["long"] != "FAIL":
                self.results["long"] = "PASS"

            self.log("SHORT CERTIFICATION")
            for sym in working:
                result = self.test_short(sym)
                if result == "DESLISTADO":
                    continue
                if result != "PASS":
                    self.results["short"] = "FAIL"
            if self.results["short"] != "FAIL":
                self.results["short"] = "PASS"

        elif MODE == "CONTINUOUS":
            self.log("=== CONTINUOUS MONITORING ===")
            self.log(f"Posiciones abiertas: {len(self.ex.get_positions())}")

        criticals = ["connection", "long", "short", "tp", "sl", "metrics"]
        if MODE == "FULL_CERTIFICATION":
            if all(self.results.get(k) == "PASS" for k in criticals):
                self.results["bot_status"] = "READY"
            else:
                self.results["bot_status"] = "NOT CERTIFIED"
        elif MODE == "CONTINUOUS":
            self.results["bot_status"] = "MONITORING"
        else:
            self.results["bot_status"] = "SAFE CHECK PASSED"

        self.finalize()

    def finalize(self):
        self.log("=" * 50)
        self.log("CERTIFICATION RESULT")
        for key in ["connection", "long", "short", "tp", "sl", "trailing", "state", "metrics"]:
            self.log(f"{key.upper()}: {self.results.get(key, 'UNKNOWN')}")
        self.log(f"BOT STATUS: {self.results['bot_status']}")
        self.log("=" * 50)

        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "w") as f:
            f.write("\n".join(self.report_lines))


if __name__ == "__main__":
    OKXCertifier().run()

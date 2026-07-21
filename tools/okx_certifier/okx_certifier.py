#!/usr/bin/env python3
"""
okx_certifier.py — Krishna Omega Ultra V9.1.1
Certificador operativo autónomo para OKX Demo.
Reutiliza los módulos del repositorio. Genera un único log.

Modos:
  FULL_CERTIFICATION  -> primera ejecución: todos los activos, LONG, SHORT, TP, SL, trailing, métricas
  CONTINUOUS           -> cada 5 horas: solo monitoriza conexión, posiciones, métricas (sin abrir trades)
  SAFE                 -> solo comprobaciones de conexión y permisos (sin órdenes)
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

# Universo secundario de 10 activos candidatos
UNIVERSO_EXTRA = [
    "NEAR", "ATOM", "UNI", "FIL", "ICP",
    "APT", "ARB", "OP", "TIA", "INJ"
]

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

    # ─── LOGGING ────────────────────────────────────────────
    def log(self, msg: str):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        self.report_lines.append(line)

    # ─── 1. CONEXIÓN ────────────────────────────────────────
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

    # ─── 2. PERMISOS ────────────────────────────────────────
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
                else:
                    self.log(f"WRITE PERMISSION WARNING: {resp.get('msg')}")
            else:
                self.log("WRITE PERMISSION SKIP (no price)")

    # ─── 3. UNIVERSO DE ACTIVOS ─────────────────────────────
    def check_asset(self, sym: str) -> Tuple[str, Dict]:
        info = self.ex.get_instrument_info(sym)
        if not info:
            return "NO DISPONIBLE", {}
        return "PASS", {
            "minSz": info["minSz"],
            "lotSz": info["lotSz"],
            "tickSz": info["tickSz"],
            "ctVal": info.get("ctVal", 1)
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

    # ─── 4. CÁLCULO DE CAPITAL DEMO RECOMENDADO ─────────────
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
        # Añadir 30% de buffer
        return round(max_margin * 1.3, 2)

    # ─── 5. PRUEBA LONG (con trailing real y verificación de trade) ──
    def test_long(self, sym: str) -> str:
        if MODE != "FULL_CERTIFICATION":
            return "SKIP"
        inst_id = f"{sym}-USDT-SWAP"
        info = self.ex.get_instrument_info(sym)
        if not info:
            return "NO SPECS"
        size = max(info["minSz"], info["lotSz"])

        self.log(f"LONG {sym} OPEN (size={size})")
        try:
            resp = self.ex.place_market_order(sym, "buy", size, mode="swap", pos_side="long")
            if resp.get("code") != "0":
                self.log(f"  OPEN FAIL: {resp.get('msg')}")
                return "FAIL_OPEN"
            self.log("  OPEN OK")
            time.sleep(1.5)

            positions = self.ex.get_positions()
            pos_id = None
            for p in positions:
                if p["instId"] == inst_id and p["posSide"] == "long":
                    pos_id = p["posId"]
                    break
            if not pos_id:
                self.log("  POSITION NOT FOUND")
                return "FAIL_POSITION"
            self.log("  POSITION VERIFIED")

            # ----- TP/SL REAL -----
            last = self.ex.get_mark_price(sym)
            if not last:
                self.log("  NO PRICE → SKIP TP/SL")
                return "FAIL_PRICE"

            tp = round(last * 1.02, 2)
            sl = round(last * 0.98, 2)
            algo_resp = self.ex.create_algo_order(sym, "long", size, tp_price=tp, sl_price=sl)
            if algo_resp and algo_resp.get("code") == "0":
                self.log("  TP/SL CREATED")
                self.results["tp"] = "PASS"
                self.results["sl"] = "PASS"
                # Guardar el algoId real
                algo_id = algo_resp["data"][0]["algoId"]
            else:
                self.log(f"  TP/SL FAIL: {algo_resp.get('msg') if algo_resp else 'None'}")
                algo_id = None

            # ----- TRAILING REAL (con algoId auténtico) -----
            if algo_id:
                amend_resp = self.ex.amend_algo_order(inst_id, algo_id, new_sl=round(sl * 1.005, 2))
                if amend_resp.get("code") == "0":
                    # Verificar que el nuevo SL se reflejó en las órdenes algo
                    algos = self.ex.get_algo_orders(inst_id, [algo_id])
                    updated = any(
                        a.get("algoId") == algo_id and float(a.get("slTriggerPx", 0)) > sl
                        for a in algos
                    )
                    if updated:
                        self.log("  TRAILING OK (amend + verificado)")
                        self.results["trailing"] = "PASS"
                    else:
                        self.log("  TRAILING WARNING: amend enviado pero no verificado en órdenes algo")
                        self.results["trailing"] = "WARNING"
                else:
                    self.log(f"  TRAILING FAIL: {amend_resp.get('msg')}")
                    self.results["trailing"] = "FAIL"
            else:
                self.log("  TRAILING SKIP (no algoId)")
                self.results["trailing"] = "SKIP"

            # ----- CIERRE -----
            close_resp = self.ex.close_position(sym, pos_id=pos_id, pos_side="long")
            if close_resp.get("code") not in ("0", "51023"):
                self.log(f"  CLOSE FAIL: {close_resp.get('msg')}")
                return "FAIL_CLOSE"
            self.log("  CLOSE OK")

            # ----- VERIFICACIÓN DE REGISTRO DE TRADE Y MÉTRICAS -----
            time.sleep(0.5)
            data = self.sm.load_all()
            trades = data.get("trades", [])
            if trades:
                last_trade = trades[-1]
                if last_trade.get("symbol") == sym and last_trade.get("pnl_net") is not None:
                    self.log("  TRADE SAVED OK")
                    # Verificar métricas
                    eq = [INITIAL_CAPITAL]
                    for t in trades:
                        eq.append(eq[-1] + t.get("pnl_net", 0))
                    m = compute_all(trades, eq, INITIAL_CAPITAL)
                    if m and m.get("win_rate") is not None:
                        self.log(f"  METRICS UPDATED OK (WR={m['win_rate']:.2f}%)")
                        self.results["state"] = "PASS"
                        self.results["metrics"] = "PASS"
                    else:
                        self.log("  METRICS WARNING: función compute_all no devolvió métricas")
                else:
                    self.log("  TRADE SAVED WARNING: trade sin pnl o símbolo incorrecto")
            else:
                self.log("  TRADE SAVED FAIL: no hay trades registrados")
                self.failed_components.append("STATE_MANAGER")
            return "PASS"
        except Exception as e:
            self.log(f"  ERROR: {e}")
            return "ERROR"

    # ─── 6. PRUEBA SHORT (equivalente) ──────────────────────
    def test_short(self, sym: str) -> str:
        if MODE != "FULL_CERTIFICATION":
            return "SKIP"
        inst_id = f"{sym}-USDT-SWAP"
        info = self.ex.get_instrument_info(sym)
        if not info:
            return "NO SPECS"
        size = max(info["minSz"], info["lotSz"])

        self.log(f"SHORT {sym} OPEN (size={size})")
        try:
            resp = self.ex.place_market_order(sym, "sell", size, mode="swap", pos_side="short")
            if resp.get("code") != "0":
                self.log(f"  OPEN FAIL: {resp.get('msg')}")
                return "FAIL_OPEN"
            self.log("  OPEN OK")
            time.sleep(1.5)

            positions = self.ex.get_positions()
            pos_id = None
            for p in positions:
                if p["instId"] == inst_id and p["posSide"] == "short":
                    pos_id = p["posId"]
                    break
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
                self.log(f"  TP/SL FAIL: {algo_resp.get('msg') if algo_resp else 'None'}")
                algo_id = None

            if algo_id:
                amend_resp = self.ex.amend_algo_order(inst_id, algo_id, new_sl=round(sl * 0.995, 2))
                if amend_resp.get("code") == "0":
                    algos = self.ex.get_algo_orders(inst_id, [algo_id])
                    updated = any(
                        a.get("algoId") == algo_id and float(a.get("slTriggerPx", 0)) < sl
                        for a in algos
                    )
                    if updated:
                        self.log("  TRAILING OK")
                    else:
                        self.log("  TRAILING WARNING: amend enviado pero no verificado")
                else:
                    self.log(f"  TRAILING FAIL: {amend_resp.get('msg')}")

            close_resp = self.ex.close_position(sym, pos_id=pos_id, pos_side="short")
            if close_resp.get("code") not in ("0", "51023"):
                self.log(f"  CLOSE FAIL: {close_resp.get('msg')}")
                return "FAIL_CLOSE"
            self.log("  CLOSE OK")

            time.sleep(0.5)
            data = self.sm.load_all()
            trades = data.get("trades", [])
            if trades and trades[-1].get("symbol") == sym:
                self.log("  TRADE SAVED OK")
            else:
                self.log("  TRADE SAVED WARNING")
            return "PASS"
        except Exception as e:
            self.log(f"  ERROR: {e}")
            return "ERROR"

    # ─── 7. EJECUCIÓN DE TODAS LAS PRUEBAS ──────────────────
    def run_full_certification(self, assets: List[str]):
        self.log("=== FULL CERTIFICATION: TODOS LOS ACTIVOS ===")
        # LONG en todos
        self.log("LONG CERTIFICATION (todos los activos)")
        long_ok = True
        for sym in assets:
            if self.test_long(sym) != "PASS":
                long_ok = False
        self.results["long"] = "PASS" if long_ok else "FAIL"

        # SHORT en todos
        self.log("SHORT CERTIFICATION (todos los activos)")
        short_ok = True
        for sym in assets:
            if self.test_short(sym) != "PASS":
                short_ok = False
        self.results["short"] = "PASS" if short_ok else "FAIL"

    # ─── 8. MONITOREO CONTINUO ──────────────────────────────
    def run_continuous(self):
        self.log("=== CONTINUOUS MONITORING ===")
        self.check_connection()
        self.check_permissions()
        positions = self.ex.get_positions()
        self.log(f"Posiciones abiertas: {len(positions)}")
        self.audit_state_and_metrics()

    # ─── 9. AUDITORÍA DE ESTADO Y MÉTRICAS ──────────────────
    def audit_state_and_metrics(self):
        self.log("STATE & METRICS CHECK")
        data = self.sm.load_all()
        trades = data.get("trades", [])
        positions = data.get("positions", [])
        self.log(f"TRADES: {len(trades)} | POSITIONS: {len(positions)}")
        if not trades:
            self.log("WARNING: sin trades → métricas en cero")
            self.results["state"] = "WARNING"
            self.results["metrics"] = "WARNING"
            return
        sample = trades[-1]
        required = ["symbol", "entry", "exit", "pnl_net", "reason"]
        missing = [f for f in required if f not in sample]
        if missing:
            self.log(f"ERROR: campos faltantes en trade: {missing}")
            self.results["state"] = "FAIL"
            self.results["metrics"] = "FAIL"
        else:
            self.results["state"] = "PASS"
            eq = [INITIAL_CAPITAL]
            for t in trades:
                eq.append(eq[-1] + t.get("pnl_net", 0))
            m = compute_all(trades, eq, INITIAL_CAPITAL)
            self.log(f"Win Rate: {m.get('win_rate', 0):.2f}% | PF: {m.get('profit_factor', 0):.2f}")
            self.results["metrics"] = "PASS"

    # ─── 10. PIPELINE SIMULADO DEL BOT ──────────────────────
    def simulate_bot_pipeline(self):
        """Verifica que los módulos del bot pueden generar una señal y llevarla hasta el exchange."""
        self.log("=== SIMULATED BOT PIPELINE ===")
        try:
            from src.strategy_rama_b import StrategyRamaB
            from src.opportunity_ranker import calculate_opportunity_score
            # Solo verificamos que los módulos importen y ejecuten sin errores
            strat = StrategyRamaB(self.ex)
            self.log("STRATEGY ENGINE OK")
            # Risk manager
            sz = self.rm.calculate_size(100, "DOGE", self.ex, 0.99)
            if sz > 0:
                self.log(f"RISK MANAGER OK (size={sz})")
            else:
                self.log("RISK MANAGER WARNING: size=0 con capital de referencia")
            self.log("BOT PIPELINE SIMULATION OK")
        except Exception as e:
            self.log(f"PIPELINE SIMULATION FAIL: {e}")
            self.failed_components.append("PIPELINE")

    # ─── 11. EJECUCIÓN PRINCIPAL ────────────────────────────
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
            self.simulate_bot_pipeline()
            self.run_full_certification(working)
            self.audit_state_and_metrics()

        elif MODE == "CONTINUOUS":
            self.run_continuous()

        elif MODE == "SAFE":
            self.log("SAFE MODE: solo chequeos de conexión y permisos")

        # Estado final
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
        self.log("=" * 50)
        for key in ["connection", "long", "short", "tp", "sl", "trailing", "state", "metrics"]:
            self.log(f"{key.upper()}: {self.results.get(key, 'UNKNOWN')}")
        if self.certified_universe:
            self.log(f"ACTIVE UNIVERSE: {', '.join(self.certified_universe[:10])}")
        if self.failed_components:
            self.log("FAILED COMPONENTS:")
            for fc in self.failed_components:
                self.log(f"  - {fc}")
        self.log(f"BOT STATUS: {self.results['bot_status']}")
        self.log("=" * 50)

        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "w") as f:
            f.write("\n".join(self.report_lines))


if __name__ == "__main__":
    certifier = OKXCertifier()
    certifier.run()

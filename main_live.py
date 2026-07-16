##############################################################
################### GITHUB CLASSIC TOKEN #####################
##############################################################

GITHUB_TOKEN = "PEGAR_AQUI_EL_TOKEN_CLASSIC"

##############################################################
##############################################################

import requests
import json
import datetime
import pathlib
import os
import sys
import time
import zipfile
import io
import re
import collections

# ------------------------------------------------------------
# Configuración fija
# ------------------------------------------------------------
REPO_OWNER = "oz10000"
REPO_NAME = "Ku-Klux-Klan"
API_BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# ------------------------------------------------------------
# Determinar la carpeta de descargas (Android / Termux)
# ------------------------------------------------------------
HOME = pathlib.Path.home()
# Prioridad para Android
ANDROID_DOWNLOAD = pathlib.Path("/storage/emulated/0/Download")
if ANDROID_DOWNLOAD.exists():
    BASE_DIR = ANDROID_DOWNLOAD / "Krishna_Audit"
else:
    # Fallback: carpeta reportes junto al script
    BASE_DIR = pathlib.Path(__file__).parent.resolve() / "reportes"

BASE_DIR.mkdir(parents=True, exist_ok=True)

# Carpeta para logs completos
LOGS_DIR = BASE_DIR / "07_logs_completos"
LOGS_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------
# Stream tee para capturar la salida en memoria
# ------------------------------------------------------------
class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

# Variable global para redirigir la salida en cada opción
output_buffer = None
original_stdout = sys.stdout

def start_capture():
    """Prepara un buffer nuevo y redirige stdout."""
    global output_buffer
    output_buffer = io.StringIO()
    sys.stdout = Tee(original_stdout, output_buffer)

def stop_capture():
    """Restaura stdout y retorna el contenido capturado."""
    global output_buffer
    sys.stdout = original_stdout
    content = output_buffer.getvalue()
    output_buffer = None
    return content

def save_captured(filename: str):
    """Detiene captura y guarda en archivo dentro de BASE_DIR."""
    content = stop_capture()
    filepath = BASE_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n[OK] Guardado: {filepath}")

# ------------------------------------------------------------
# Funciones de petición con reintentos
# ------------------------------------------------------------
def make_request(url, params=None, stream=False, retries=3):
    """Realiza una petición GET con reintentos y manejo de rate limit."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, stream=stream, timeout=30)
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                reset_time = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset_time - time.time(), 1) + 5
                print(f"Rate limit alcanzado, esperando {wait:.0f} segundos...")
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                print(f"Error servidor {resp.status_code}, reintento {attempt+1}/{retries}...")
                time.sleep(5)
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            print(f"Error de red: {e}, reintento {attempt+1}/{retries}...")
            time.sleep(5)
    print(f"NO DISPONIBLE: falló la petición a {url}")
    return None

def get_all_pages(url, params=None, list_key=None):
    """Recorre paginación y devuelve todos los elementos."""
    items = []
    page = 1
    while True:
        p = params.copy() if params else {}
        p["per_page"] = 100
        p["page"] = page
        resp = make_request(url, params=p)
        if resp is None:
            break
        data = resp.json()
        if list_key:
            chunk = data.get(list_key, [])
        else:
            chunk = data if isinstance(data, list) else []
        if not chunk:
            break
        items.extend(chunk)
        link = resp.headers.get("Link", "")
        if 'rel="next"' not in link:
            break
        page += 1
    return items

# ------------------------------------------------------------
# Opción 1: Información del repositorio
# ------------------------------------------------------------
def opcion_1():
    start_capture()
    print("="*60)
    print("INFORMACION DEL REPOSITORIO")
    print("-"*40)
    url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}"
    resp = make_request(url)
    if resp:
        repo = resp.json()
        print(f"Nombre: {repo.get('full_name', 'NO DISPONIBLE')}")
        print(f"Owner: {repo.get('owner', {}).get('login', 'NO DISPONIBLE')}")
        desc = repo.get('description') or 'NO DISPONIBLE'
        print(f"Descripcion: {desc}")
        print(f"Publico/Privado: {'publico' if not repo.get('private', True) else 'privado'}")
        print(f"Fecha de creacion: {repo.get('created_at', 'NO DISPONIBLE')}")
        print(f"Fecha de actualizacion: {repo.get('updated_at', 'NO DISPONIBLE')}")
        print(f"Ultimo push: {repo.get('pushed_at', 'NO DISPONIBLE')}")
        print(f"Branch principal: {repo.get('default_branch', 'NO DISPONIBLE')}")
        print(f"Lenguaje principal: {repo.get('language', 'NO REPORTADO') or 'NO REPORTADO'}")
        print(f"Tamanio (KB): {repo.get('size', 'NO DISPONIBLE')}")
        print(f"Forks: {repo.get('forks_count', 'NO DISPONIBLE')}")
        print(f"Stars: {repo.get('stargazers_count', 'NO DISPONIBLE')}")
        print(f"Watchers: {repo.get('watchers_count', 'NO DISPONIBLE')}")
        print(f"Open Issues: {repo.get('open_issues_count', 'NO DISPONIBLE')}")
        lic = repo.get('license')
        if lic and isinstance(lic, dict):
            print(f"License: {lic.get('spdx_id', 'NO DISPONIBLE')}")
        else:
            print("License: NO DISPONIBLE")
        topics = repo.get('topics', [])
        print(f"Topics: {', '.join(topics) if topics else 'NO DISPONIBLE'}")
    else:
        print("NO SE PUDO OBTENER INFORMACION DEL REPOSITORIO")
    save_captured("01_repositorio.txt")

# ------------------------------------------------------------
# Opción 2: Commits completos
# ------------------------------------------------------------
def opcion_2():
    start_capture()
    print("="*60)
    print("COMMITS")
    print("="*60)
    commits_url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    commits = get_all_pages(commits_url)
    if not commits:
        print("NO DISPONIBLE")
    else:
        for i, commit_summary in enumerate(commits, 1):
            sha = commit_summary.get('sha', '')
            short_sha = sha[:7] if sha else 'NO DISPONIBLE'
            commit_node = commit_summary.get('commit', {})
            author_info = commit_node.get('author', {})
            author_name = author_info.get('name', 'NO DISPONIBLE')
            date_str = author_info.get('date', 'NO DISPONIBLE')
            message = commit_node.get('message', 'NO DISPONIBLE').strip()
            print(f"\n--- Commit #{i} ---")
            print(f"SHA: {sha}")
            print(f"SHA corto: {short_sha}")
            print(f"Autor: {author_name}")
            print(f"Fecha: {date_str}")
            print(f"Mensaje: {message}")
            # Archivos afectados
            detail_url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/commits/{sha}"
            detail_resp = make_request(detail_url)
            if detail_resp:
                files = detail_resp.json().get('files', [])
                if files:
                    print("Archivos modificados:")
                    for f in files:
                        fname = f.get('filename', 'NO DISPONIBLE')
                        status = f.get('status', 'NO DISPONIBLE')
                        print(f"  {fname} ({status})")
                else:
                    print("Archivos modificados: NO REPORTADO")
            else:
                print("Archivos modificados: NO DISPONIBLE")
    save_captured("02_commits.txt")

# ------------------------------------------------------------
# Opción 3: Archivos modificados por commits
# ------------------------------------------------------------
def opcion_3():
    start_capture()
    print("="*60)
    print("ARCHIVOS MODIFICADOS (lista consolidada)")
    print("="*60)
    all_files = set()
    commits_url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    commits = get_all_pages(commits_url)
    if not commits:
        print("NO DISPONIBLE")
    else:
        for c in commits:
            sha = c.get('sha', '')
            detail_url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/commits/{sha}"
            detail_resp = make_request(detail_url)
            if detail_resp:
                for f in detail_resp.json().get('files', []):
                    fname = f.get('filename', '')
                    status = f.get('status', '')
                    all_files.add(f"{fname} ({status})")
        if all_files:
            for entry in sorted(all_files):
                print(entry)
        else:
            print("NO DISPONIBLE")
    save_captured("03_archivos_modificados.txt")

# ------------------------------------------------------------
# Opción 4: Workflows
# ------------------------------------------------------------
def opcion_4():
    start_capture()
    print("="*60)
    print("WORKFLOWS")
    print("="*60)
    url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows"
    resp = make_request(url)
    if resp:
        workflows = resp.json().get('workflows', [])
        if not workflows:
            print("NO DISPONIBLE")
        else:
            for wf in workflows:
                print(f"\nNombre: {wf.get('name', 'NO DISPONIBLE')}")
                print(f"Archivo YAML: {wf.get('path', 'NO DISPONIBLE')}")
                print(f"Estado: {wf.get('state', 'NO DISPONIBLE')}")
                print(f"Fecha creacion: {wf.get('created_at', 'NO DISPONIBLE')}")
                print(f"Fecha actualizacion: {wf.get('updated_at', 'NO DISPONIBLE')}")
    else:
        print("NO DISPONIBLE")
    save_captured("04_workflows.txt")

# ------------------------------------------------------------
# Opción 5: Action Runs
# ------------------------------------------------------------
def opcion_5():
    start_capture()
    print("="*60)
    print("ACTION RUNS")
    print("="*60)
    runs_url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs"
    runs = get_all_pages(runs_url, list_key="workflow_runs")
    if not runs:
        print("NO DISPONIBLE")
    else:
        for run in runs:
            run_id = run.get('id', 'NO DISPONIBLE')
            run_number = run.get('run_number', 'NO DISPONIBLE')
            workflow_name = run.get('name', 'NO DISPONIBLE')
            branch = run.get('head_branch', 'NO DISPONIBLE')
            head_sha = run.get('head_sha', 'NO DISPONIBLE')
            actor = run.get('actor', {})
            actor_login = actor.get('login', 'NO DISPONIBLE') if isinstance(actor, dict) else 'NO DISPONIBLE'
            event = run.get('event', 'NO DISPONIBLE')
            status = run.get('status', 'NO DISPONIBLE')
            conclusion = run.get('conclusion', 'NO DISPONIBLE')
            created_at = run.get('created_at', 'NO DISPONIBLE')
            updated_at = run.get('updated_at', 'NO DISPONIBLE')
            run_url = run.get('html_url', 'NO DISPONIBLE')
            # Duración
            duration = "NO DISPONIBLE"
            if created_at != 'NO DISPONIBLE' and updated_at != 'NO DISPONIBLE':
                try:
                    start_dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    end_dt = datetime.datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    duration = str(end_dt - start_dt)
                except:
                    pass
            print(f"\nRun ID: {run_id}")
            print(f"Run Number: {run_number}")
            print(f"Workflow: {workflow_name}")
            print(f"Estado: {status}")
            print(f"Conclusion: {conclusion}")
            print(f"Branch: {branch}")
            print(f"Commit: {head_sha[:7] if isinstance(head_sha, str) else head_sha}")
            print(f"Autor: {actor_login}")
            print(f"Evento: {event}")
            print(f"Fecha inicio: {created_at}")
            print(f"Fecha fin: {updated_at}")
            print(f"Duracion: {duration}")
            print(f"URL: {run_url}")
    save_captured("05_action_runs.txt")

# ------------------------------------------------------------
# Opción 6: Artifacts
# ------------------------------------------------------------
def opcion_6():
    start_capture()
    print("="*60)
    print("ARTIFACTS")
    print("="*60)
    url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/artifacts"
    artifacts = get_all_pages(url, list_key="artifacts")
    if not artifacts:
        print("NO DISPONIBLE")
    else:
        for art in artifacts:
            print(f"\nNombre: {art.get('name', 'NO DISPONIBLE')}")
            print(f"ID: {art.get('id', 'NO DISPONIBLE')}")
            print(f"Tamaño (bytes): {art.get('size_in_bytes', 'NO DISPONIBLE')}")
            print(f"Fecha creacion: {art.get('created_at', 'NO DISPONIBLE')}")
            print(f"Fecha expiracion: {art.get('expires_at', 'NO DISPONIBLE')}")
            expired = art.get('expired', False)
            print(f"Estado: {'expirado' if expired else 'activo'}")
            print(f"URL: {art.get('archive_download_url', 'NO DISPONIBLE')}")
    save_captured("06_artifacts.txt")

# ------------------------------------------------------------
# Opción 7: Logs completos
# ------------------------------------------------------------
def opcion_7():
    start_capture()
    print("="*60)
    print("DESCARGANDO LOGS COMPLETOS DE TODOS LOS RUNS")
    print("="*60)
    runs_url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs"
    runs = get_all_pages(runs_url, list_key="workflow_runs")
    if not runs:
        print("NO HAY RUNS DISPONIBLES")
        save_captured("07_logs_completos_resumen.txt")
        return
    # La salida en consola será un resumen; los logs reales van a archivos individuales
    for idx, run in enumerate(runs, 1):
        run_id = run.get('id')
        if not run_id:
            continue
        print(f"\n[+] Descargando logs para run {run_id} ({idx}/{len(runs)})...")
        logs_url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}/logs"
        log_resp = make_request(logs_url, stream=True)
        if log_resp is None or log_resp.status_code != 200:
            print(f"  ERROR: No se pudo descargar (status {log_resp.status_code if log_resp else 'error'})")
            continue
        try:
            zip_content = io.BytesIO(log_resp.content)
            with zipfile.ZipFile(zip_content) as zf:
                for file_name in zf.namelist():
                    # Guardar cada archivo del zip en la carpeta de logs
                    safe_name = f"run_{idx:04d}_{file_name.replace('/', '_')}"
                    filepath = LOGS_DIR / safe_name
                    with zf.open(file_name) as f:
                        content = f.read()
                    with open(filepath, "wb") as out:
                        out.write(content)
                    print(f"  [OK] Guardado: {filepath}")
        except zipfile.BadZipFile:
            print("  ERROR: El archivo descargado no es un zip válido")
        except Exception as e:
            print(f"  ERROR procesando logs: {e}")
    print("\n[COMPLETADO] Todos los logs descargados en la carpeta 07_logs_completos")
    save_captured("07_logs_completos_resumen.txt")

# ------------------------------------------------------------
# Opción 8: Búsqueda de eventos en logs
# ------------------------------------------------------------
def opcion_8():
    start_capture()
    print("="*60)
    print("BUSQUEDA DE EVENTOS EN LOGS")
    print("="*60)
    SEARCH_TERMS = [
        "ERROR", "WARNING", "CRITICAL", "Traceback", "Exception",
        "Kill Switch", "Kill switch", "PnL", "Trades", "Drawdown",
        "SL", "TP", "Trailing", "Velocity", "Repair",
        "51008", "51023", "51280", "API error",
        "Balance", "Risk", "Position", "Strategy", "Exchange"
    ]
    runs_url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs"
    runs = get_all_pages(runs_url, list_key="workflow_runs")
    if not runs:
        print("NO HAY RUNS DISPONIBLES")
        save_captured("08_logs_filtrados.txt")
        return
    total_found = 0
    for idx, run in enumerate(runs, 1):
        run_id = run.get('id')
        if not run_id:
            continue
        print(f"\n[+] Revisando logs del run {run_id} ({idx}/{len(runs)})...")
        logs_url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}/logs"
        log_resp = make_request(logs_url, stream=True)
        if log_resp is None or log_resp.status_code != 200:
            continue
        try:
            zip_content = io.BytesIO(log_resp.content)
            with zipfile.ZipFile(zip_content) as zf:
                for file_name in zf.namelist():
                    with zf.open(file_name) as f:
                        lines = f.read().decode('utf-8', errors='replace').splitlines()
                    found_in_file = False
                    for line in lines:
                        if any(term in line for term in SEARCH_TERMS):
                            if not found_in_file:
                                print(f"\n  Archivo: {file_name}")
                                found_in_file = True
                            print(f"    {line.strip()}")
                            total_found += 1
        except Exception as e:
            print(f"  Error procesando logs del run {run_id}: {e}")
    print(f"\nTotal de lineas relevantes encontradas: {total_found}")
    save_captured("08_logs_filtrados.txt")

# ------------------------------------------------------------
# Opción 9: Métricas encontradas en logs
# ------------------------------------------------------------
def opcion_9():
    start_capture()
    print("="*60)
    print("METRICAS ENCONTRADAS EN LOGS")
    print("="*60)
    METRIC_TERMS = [
        "PnL/hora", "Trades/hora", "Win Rate", "Profit Factor",
        "Sharpe", "Sortino", "Calmar", "Recovery", "Drawdown",
        "Balance", "Equity", "Capital", "Expectancy"
    ]
    runs_url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs"
    runs = get_all_pages(runs_url, list_key="workflow_runs")
    if not runs:
        print("NO HAY RUNS DISPONIBLES")
        save_captured("09_metricas_encontradas.txt")
        return
    found_metrics = []
    for idx, run in enumerate(runs, 1):
        run_id = run.get('id')
        if not run_id:
            continue
        print(f"[+] Buscando métricas en run {run_id} ({idx}/{len(runs)})...")
        logs_url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}/logs"
        log_resp = make_request(logs_url, stream=True)
        if log_resp is None or log_resp.status_code != 200:
            continue
        try:
            zip_content = io.BytesIO(log_resp.content)
            with zipfile.ZipFile(zip_content) as zf:
                for file_name in zf.namelist():
                    with zf.open(file_name) as f:
                        lines = f.read().decode('utf-8', errors='replace').splitlines()
                    for line in lines:
                        if any(mterm in line for mterm in METRIC_TERMS):
                            found_metrics.append(f"[{file_name}] {line.strip()}")
        except Exception:
            continue
    if found_metrics:
        for m in found_metrics:
            print(m)
    else:
        print("NO ENCONTRADO")
    save_captured("09_metricas_encontradas.txt")

# ------------------------------------------------------------
# Opción 10: Reporte forense completo
# ------------------------------------------------------------
def opcion_10():
    # Simplemente ejecuta todas las opciones y concatena en un solo archivo
    start_capture()
    print("="*60)
    print("REPORTE FORENSE COMPLETO")
    print("="*60)
    # Opción 1
    opcion_1()
    content1 = stop_capture()  # ya guardó su archivo, pero necesitamos la salida
    # Volvemos a capturar para seguir
    start_capture()
    opcion_2()
    content2 = stop_capture()
    start_capture()
    opcion_3()
    content3 = stop_capture()
    start_capture()
    opcion_4()
    content4 = stop_capture()
    start_capture()
    opcion_5()
    content5 = stop_capture()
    start_capture()
    opcion_6()
    content6 = stop_capture()
    # Opción 8 (eventos) y 9 (métricas) se incluyen en el reporte completo
    start_capture()
    opcion_8()
    content8 = stop_capture()
    start_capture()
    opcion_9()
    content9 = stop_capture()
    # Unir todo
    full_report = (
        content1 + "\n" + content2 + "\n" + content3 + "\n" +
        content4 + "\n" + content5 + "\n" + content6 + "\n" +
        content8 + "\n" + content9
    )
    filepath = BASE_DIR / "10_reporte_forense_completo.txt"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_report)
    print(f"\n[OK] Reporte completo guardado en {filepath}")
    # También se muestra en consola lo que se fue ejecutando, pero no repetimos la salida
    # (ya se imprimió en cada opcion). Para que no se pierda, al menos avisamos.
    stop_capture()  # limpia

# ------------------------------------------------------------
# Opción 11: Ejecutar todas las opciones automáticamente
# ------------------------------------------------------------
def opcion_11():
    print("\n[+] Ejecutando todas las opciones...")
    opcion_1()
    opcion_2()
    opcion_3()
    opcion_4()
    opcion_5()
    opcion_6()
    opcion_7()
    opcion_8()
    opcion_9()
    # El reporte completo ya es un subconjunto, pero podemos generarlo igual
    opcion_10()
    print("\n[COMPLETADO] Todas las extracciones finalizadas.")

# ------------------------------------------------------------
# Menú interactivo
# ------------------------------------------------------------
def mostrar_menu():
    print("\n" + "="*60)
    print("KRISHNA OMEGA ULTRA")
    print("REPOSITORIO FORENSIC AUDITOR")
    print("="*60)
    print("\nSELECCIONA INFORMACION A EXTRAER:\n")
    print("[1] Informacion general del repositorio")
    print("[2] Commits completos")
    print("[3] Archivos modificados por commits")
    print("[4] Workflows GitHub Actions")
    print("[5] Runs completos")
    print("[6] Artifacts")
    print("[7] Logs completos")
    print("[8] Busqueda de errores en logs")
    print("[9] Metricas encontradas en logs")
    print("[10] Informe forense completo")
    print("[11] Descargar todo")
    print("[0] Salir")
    print("="*60)

def main():
    # Asegurarse de que exista la carpeta base
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

    while True:
        mostrar_menu()
        try:
            opcion = input("\nElegir opcion: ").strip()
        except KeyboardInterrupt:
            print("\nSaliendo...")
            break

        if opcion == "1":
            print("\n[+] Extrayendo informacion del repositorio...")
            opcion_1()
        elif opcion == "2":
            print("\n[+] Extrayendo commits...")
            opcion_2()
        elif opcion == "3":
            print("\n[+] Extrayendo archivos modificados...")
            opcion_3()
        elif opcion == "4":
            print("\n[+] Extrayendo workflows...")
            opcion_4()
        elif opcion == "5":
            print("\n[+] Extrayendo action runs...")
            opcion_5()
        elif opcion == "6":
            print("\n[+] Extrayendo artifacts...")
            opcion_6()
        elif opcion == "7":
            print("\n[+] Descargando logs completos...")
            opcion_7()
        elif opcion == "8":
            print("\n[+] Buscando eventos en logs...")
            opcion_8()
        elif opcion == "9":
            print("\n[+] Buscando metricas...")
            opcion_9()
        elif opcion == "10":
            print("\n[+] Generando reporte forense completo...")
            opcion_10()
        elif opcion == "11":
            opcion_11()
        elif opcion == "0":
            print("Saliendo del auditor forense.")
            break
        else:
            print("Opcion no valida. Intenta de nuevo.")

if __name__ == "__main__":
    main()

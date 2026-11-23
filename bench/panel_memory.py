"""Critère d'acceptation v1 : le panneau tourne sans fuite mémoire (prévu sur 24 h).

Se connecte à Chrome sur le téléphone (débogage USB + DevTools), trouve l'onglet du panneau et,
à intervalle régulier : force un ramasse-miettes, relève le tas JS, le nombre de nœuds DOM et
d'écouteurs, ainsi que la mémoire de l'agent sur le PC. Écrit un CSV et donne la pente (Mo/h).

Prérequis : téléphone branché, débogage USB autorisé, panneau ouvert dans Chrome
(http://localhost:8765 via « adb reverse tcp:8765 tcp:8765 »), écran allumé.

Usage : .\\.venv\\Scripts\\python bench\\panel_memory.py [--minutes 10] [--interval 60]
"""

import argparse
import base64
import csv
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
DEVTOOLS_PORT = 9222
PANEL_PREFIX = "http://localhost:8765"
AGENT_PORT = 8765


# --- adb ------------------------------------------------------------------------------


def adb_path() -> str:
    found = shutil.which("adb")
    if found:
        return found
    sdk = Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe"
    if sdk.exists():
        return str(sdk)
    raise SystemExit("adb introuvable (Android SDK platform-tools)")


def adb(*args: str) -> str:
    result = subprocess.run([adb_path(), *args], capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise SystemExit(f"adb {' '.join(args)} : {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


# --- Client WebSocket minimal (RFC 6455, trames texte, côté client) -------------------


class WebSocket:
    def __init__(self, url: str, timeout: float = 30):
        parts = urllib.parse.urlsplit(url)
        self.sock = socket.create_connection((parts.hostname, parts.port or 80), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        request = (
            f"GET {path} HTTP/1.1\r\nHost: {parts.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode())
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("poignée de main WebSocket interrompue")
            response += chunk
        status_line = response.split(b"\r\n", 1)[0]
        if b" 101 " not in status_line:
            raise ConnectionError(f"WebSocket refusé : {status_line!r}")
        self.buffer = response.split(b"\r\n\r\n", 1)[1]

    def _read(self, n: int) -> bytes:
        while len(self.buffer) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("WebSocket fermé par Chrome")
            self.buffer += chunk
        data, self.buffer = self.buffer[:n], self.buffer[n:]
        return data

    def send(self, text: str) -> None:
        payload = text.encode()
        header = bytearray([0x81])  # FIN + trame texte
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.sock.sendall(bytes(header) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def recv(self) -> str:
        message = b""
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7F
            if n == 126:
                (n,) = struct.unpack(">H", self._read(2))
            elif n == 127:
                (n,) = struct.unpack(">Q", self._read(8))
            payload = self._read(n)
            opcode = b1 & 0x0F
            if opcode == 0x8:
                raise ConnectionError("WebSocket fermé par Chrome")
            if opcode in (0x9, 0xA):  # ping / pong : ignorés
                continue
            message += payload
            if b1 & 0x80:  # FIN
                return message.decode()

    def close(self) -> None:
        self.sock.close()


class DevTools:
    def __init__(self, ws_url: str):
        self.ws = WebSocket(ws_url)
        self.next_id = 0

    def call(self, method: str, **params) -> dict:
        self.next_id += 1
        self.ws.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        while True:  # on ignore les événements jusqu'à la réponse attendue
            message = json.loads(self.ws.recv())
            if message.get("id") == self.next_id:
                if "error" in message:
                    raise RuntimeError(f"{method} : {message['error']}")
                return message.get("result", {})


# --- Mesures ----------------------------------------------------------------------------


def find_panel_tab() -> tuple[dict, DevTools]:
    """Onglet du panneau VISIBLE : un onglet en arrière-plan est gelé par Chrome, sa mesure ne dirait rien."""
    with urllib.request.urlopen(f"http://127.0.0.1:{DEVTOOLS_PORT}/json", timeout=5) as response:
        tabs = json.load(response)
    panels = [t for t in tabs if t.get("type") == "page" and t.get("url", "").startswith(PANEL_PREFIX)]
    if not panels:
        raise SystemExit(f"aucun onglet {PANEL_PREFIX} ouvert dans Chrome sur le téléphone")
    for tab in panels:
        tools = DevTools(tab["webSocketDebuggerUrl"])
        state = tools.call("Runtime.evaluate", expression="document.visibilityState", returnByValue=True)
        if state["result"].get("value") == "visible":
            if len(panels) > 1:
                print(f"{len(panels)} onglets du panneau ouverts : mesure de l'onglet visible.", flush=True)
            return tab, tools
        tools.ws.close()
    raise SystemExit("aucun onglet du panneau n'est visible : allumer l'écran et afficher le panneau")


def agent_rss_mb() -> float | None:
    """Mémoire du processus qui écoute sur 8765 (le serveur, pas son lanceur)."""
    try:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.laddr and conn.laddr.port == AGENT_PORT and conn.status == psutil.CONN_LISTEN and conn.pid:
                return round(psutil.Process(conn.pid).memory_info().rss / 2**20, 1)
    except (psutil.Error, OSError):
        pass
    return None


def sample(tools: DevTools) -> dict:
    tools.call("HeapProfiler.collectGarbage")
    metrics = {m["name"]: m["value"] for m in tools.call("Performance.getMetrics")["metrics"]}
    return {
        "heure": datetime.now().strftime("%H:%M:%S"),
        "tas_js_mo": round(metrics.get("JSHeapUsedSize", 0) / 2**20, 2),
        "noeuds_dom": int(metrics.get("Nodes", 0)),
        "ecouteurs": int(metrics.get("JSEventListeners", 0)),
        "agent_mo": agent_rss_mb(),
    }


def slope_per_hour(times_s: list[float], values: list[float]) -> float:
    """Pente par moindres carrés, en unités par heure."""
    n = len(values)
    if n < 2:
        return 0.0
    mt, mv = sum(times_s) / n, sum(values) / n
    var = sum((t - mt) ** 2 for t in times_s)
    if var == 0:
        return 0.0
    return sum((t - mt) * (v - mv) for t, v in zip(times_s, values)) / var * 3600


# --- Programme ------------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--minutes", type=float, default=10, help="durée (1440 pour l'essai de 24 h)")
    parser.add_argument("--interval", type=float, default=60, help="secondes entre deux relevés")
    parser.add_argument("--csv", type=Path, default=None, help="fichier de sortie (défaut : bench/results/)")
    args = parser.parse_args()

    out = args.csv or ROOT / "bench" / "results" / f"panel_memory-{datetime.now():%Y%m%d-%H%M}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    adb("forward", f"tcp:{DEVTOOLS_PORT}", "localabstract:chrome_devtools_remote")
    rows: list[dict] = []
    times: list[float] = []
    try:
        tab, tools = find_panel_tab()
        tools.call("Performance.enable")
        print(f"Onglet : {tab['url'].split('?')[0]} — {args.minutes:g} min, relevé toutes les {args.interval:g} s", flush=True)

        start = time.monotonic()
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["heure", "tas_js_mo", "noeuds_dom", "ecouteurs", "agent_mo"])
            writer.writeheader()
            while True:
                row = sample(tools)
                rows.append(row)
                times.append(time.monotonic() - start)
                writer.writerow(row)
                f.flush()
                print(
                    f"  {row['heure']}  tas JS {row['tas_js_mo']:6.2f} Mo  nœuds {row['noeuds_dom']:5}  "
                    f"écouteurs {row['ecouteurs']:4}  agent {row['agent_mo']} Mo",
                    flush=True,
                )
                if time.monotonic() - start + args.interval > args.minutes * 60:
                    break
                time.sleep(args.interval)
        tools.ws.close()
    finally:
        subprocess.run([adb_path(), "forward", "--remove", f"tcp:{DEVTOOLS_PORT}"], capture_output=True, timeout=15)

    heap = [r["tas_js_mo"] for r in rows]
    nodes = [r["noeuds_dom"] for r in rows]
    agent = [r["agent_mo"] for r in rows if r["agent_mo"] is not None]
    summary = {
        "releves": len(rows),
        "tas_js_mo": f"{heap[0]} -> {heap[-1]} (min {min(heap)}, max {max(heap)})",
        "tas_js_pente_mo_h": round(slope_per_hour(times, heap), 3),
        "noeuds_dom": f"{nodes[0]} -> {nodes[-1]} (max {max(nodes)})",
        "agent_mo": f"{agent[0]} -> {agent[-1]}" if agent else "inconnu",
        "csv": str(out.relative_to(ROOT)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if len(rows) < 10 or times[-1] < 3600:
        print("Indicatif seulement : il faut plusieurs heures pour distinguer un plateau d'une fuite lente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

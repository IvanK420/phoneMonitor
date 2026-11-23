"""Critère d'acceptation v1 : l'agent consomme moins de 2 % de CPU au repos.

Lance l'agent dans un processus séparé, l'interroge comme le panneau (/api/stats et /api/ai
toutes les 2 s) pendant N minutes, et mesure le temps CPU consommé par ce processus.

Usage : .\\.venv\\Scripts\\python bench\\idle_cpu.py [--minutes 10] [--port 8766] [--limit 2]

Résultat principal : % de la machine entière (comme le Gestionnaire des tâches). Le % d'un cœur
est donné pour information. Ne mesure pas les processus nvidia-smi éphémères (absents ici).
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.config import load_config  # noqa: E402

POLL_S = 2.0
WARMUP_S = 10.0


def get(url: str, token: str) -> int:
    request = urllib.request.Request(url, headers={"X-Token": token})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except OSError:
        return 0


def wait_ready(base: str, timeout_s: float = 20) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base}/healthz", timeout=1):
                return
        except OSError:
            time.sleep(0.3)
    raise SystemExit("l'agent n'a pas démarré à temps")


def process_tree(root: psutil.Process) -> list[psutil.Process]:
    """Sous Windows, le python.exe d'un venv est un lanceur : le vrai serveur est son enfant."""
    return [root, *root.children(recursive=True)]


def cpu_seconds(tree: list[psutil.Process]) -> float:
    total = 0.0
    for p in tree:
        t = p.cpu_times()
        total += t.user + t.system
    return total


def rss_bytes(tree: list[psutil.Process]) -> int:
    return sum(p.memory_info().rss for p in tree)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--minutes", type=float, default=10)
    parser.add_argument("--port", type=int, default=8766, help="port de l'agent mesuré (≠ 8765 pour ne pas gêner)")
    parser.add_argument("--limit", type=float, default=2.0, help="seuil en % de la machine")
    args = parser.parse_args()

    token = load_config()["token"]
    base = f"http://127.0.0.1:{args.port}"
    agent = subprocess.Popen(
        [sys.executable, "-m", "agent", "--port", str(args.port)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_ready(base)
        tree = process_tree(psutil.Process(agent.pid))
        print(f"Processus mesurés : {', '.join(f'{p.name()}[{p.pid}]' for p in tree)}", flush=True)
        cores = psutil.cpu_count(logical=True) or 1

        def poll() -> list[int]:
            return [get(f"{base}/api/stats", token), get(f"{base}/api/ai", token)]

        # Préchauffage : premier relevé psutil, imports paresseux, caches…
        warm_end = time.monotonic() + WARMUP_S
        while time.monotonic() < warm_end:
            poll()
            time.sleep(POLL_S)

        rss_start = rss_bytes(tree)
        cpu_start, wall_start = cpu_seconds(tree), time.monotonic()
        duration = args.minutes * 60
        requests = errors = 0
        next_report = 60.0
        print(f"Mesure sur {args.minutes:g} min ({cores} cœurs logiques), sondage toutes les {POLL_S:g} s…", flush=True)

        while (elapsed := time.monotonic() - wall_start) < duration:
            codes = poll()
            requests += len(codes)
            errors += sum(code != 200 for code in codes)
            if elapsed >= next_report:
                used = cpu_seconds(tree) - cpu_start
                print(f"  {elapsed / 60:4.1f} min : {used / elapsed * 100 / cores:5.2f} % machine", flush=True)
                next_report += 60
            time.sleep(POLL_S)

        wall = time.monotonic() - wall_start
        used = cpu_seconds(tree) - cpu_start
        rss_end = rss_bytes(tree)
    finally:
        agent.terminate()
        try:
            agent.wait(timeout=10)
        except subprocess.TimeoutExpired:
            agent.kill()

    one_core = used / wall * 100
    machine = one_core / cores
    result = {
        "duree_s": round(wall),
        "requetes": requests,
        "erreurs": errors,
        "cpu_s": round(used, 2),
        "cpu_pct_machine": round(machine, 3),
        "cpu_pct_un_coeur": round(one_core, 3),
        "rss_debut_mo": round(rss_start / 2**20, 1),
        "rss_fin_mo": round(rss_end / 2**20, 1),
    }
    ok = machine < args.limit and errors == 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"{'OK' if ok else 'ÉCHEC'} : {machine:.2f} % de la machine (seuil {args.limit:g} %), {errors} erreur(s)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

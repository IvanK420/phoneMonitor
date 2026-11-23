"""Sessions IA (Claude Code, Codex) — logique pure + lecture tolérante des fichiers de session.

Sécurité (04-securite-planning.md) : on ne renvoie jamais le contenu d'une session,
seulement outil, nom de projet, état et date. Les fichiers `*.key` ne sont jamais ouverts.
"""

import json
import re
import time
from collections.abc import Callable
from pathlib import Path

UNKNOWN_PROJECT = "?"
_PATH_SEPARATORS = re.compile(r"[/\\]")
WORKING_UNDER_S = 10
STALE_FROM_S = 600

_EXPLICIT_STATES = {"busy": "working", "idle": "idle"}

CODEX_MAX_SESSIONS = 20
_CODEX_SUFFIXES = {".jsonl", ".json"}


def classify(age_s: float) -> str:
    """Heuristique v1 : modifié il y a < 10 s → working ; < 10 min → idle ; sinon stale."""
    if age_s < WORKING_UNDER_S:
        return "working"
    if age_s < STALE_FROM_S:
        return "idle"
    return "stale"


def session_state(status: object, age_s: float, alive: bool | None = None) -> str:
    """Le statut explicite (`busy` / `idle`) prime sur l'âge du fichier.

    `alive` = le processus de la session tourne-t-il encore (None : inconnu) :
    - processus mort → stale (session terminée ou plantée) ;
    - `busy` + processus vivant → working quel que soit l'âge (updatedAt reste figé
      au début d'une longue tâche) ;
    - sinon, une session figée depuis 10 min est stale.
    """
    if alive is False:
        return "stale"
    if status == "busy" and alive is True:
        return "working"
    heuristic = classify(age_s)
    if heuristic == "stale":
        return "stale"
    return _EXPLICIT_STATES.get(status, heuristic) if isinstance(status, str) else heuristic


def project_name(cwd: object) -> str:
    """Dernier segment du dossier de travail (chemins Windows ou POSIX) ; jamais le chemin complet."""
    if not isinstance(cwd, str):
        return UNKNOWN_PROJECT
    name = _PATH_SEPARATORS.split(cwd.rstrip("/\\"))[-1]
    if not name or name.endswith(":"):  # "", "/" ou une racine de lecteur "C:\"
        return UNKNOWN_PROJECT
    return name


def _is_number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def parse_claude(text: str, mtime: float) -> dict:
    """Lit un `~/.claude/sessions/<pid>.json`. Tout champ absent ou invalide retombe sur un défaut :
    projet « ? », date = mtime du fichier, statut inconnu."""
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if not isinstance(data, dict):
        data = {}

    stamps_ms = [v for v in (data.get("updatedAt"), data.get("statusUpdatedAt")) if _is_number(v)]
    status = data.get("status")
    pid = data.get("pid")
    return {
        "project": project_name(data.get("cwd")),
        "updated_at": int(max(stamps_ms) // 1000) if stamps_ms else int(mtime),
        "status": status if isinstance(status, str) else None,
        "pid": pid if isinstance(pid, int) and not isinstance(pid, bool) else None,  # interne, jamais exposé
    }


PidAlive = Callable[[int], bool]


def _liveness(pid: int | None, pid_alive: PidAlive | None) -> bool | None:
    if pid is None or pid_alive is None:
        return None
    try:
        return bool(pid_alive(pid))
    except Exception:  # noqa: BLE001 — accès refusé, etc. : on ne sait pas
        return None


def _public(tool: str, project: str, updated_at: int, state: str) -> dict:
    """Seuls champs exposés par /api/ai : aucune autre donnée de session ne sort d'ici."""
    return {"tool": tool, "project": project, "state": state, "updated_at": updated_at}


def scan_claude(directory: Path, now: float, pid_alive: PidAlive | None = None) -> list[dict]:
    """Parcourt `~/.claude/sessions`. N'ouvre QUE les `*.json` : les `*.key` contiennent des secrets."""
    if not directory.is_dir():
        return []
    sessions = []
    for path in directory.glob("*.json"):
        try:
            if not path.is_file():
                continue
            mtime = path.stat().st_mtime
            parsed = parse_claude(path.read_text(encoding="utf-8", errors="replace"), mtime=mtime)
        except OSError:  # session terminée entre le listage et la lecture, accès refusé…
            continue
        alive = _liveness(parsed["pid"], pid_alive)
        state = session_state(parsed["status"], age_s=now - parsed["updated_at"], alive=alive)
        sessions.append(_public("claude-code", parsed["project"], parsed["updated_at"], state))
    return sessions


def scan_codex(directory: Path, now: float) -> list[dict]:
    """Parcourt `~/.codex/sessions` (format non documenté, absent de ce PC) : un fichier = une session,
    datée par son mtime. Le contenu n'est jamais lu. Seuls les `CODEX_MAX_SESSIONS` plus récents sont gardés."""
    if not directory.is_dir():
        return []
    stamps = []
    for path in directory.rglob("*"):
        if path.suffix not in _CODEX_SUFFIXES:
            continue
        try:
            if path.is_file():
                stamps.append(path.stat().st_mtime)
        except OSError:
            continue
    recent = sorted(stamps, reverse=True)[:CODEX_MAX_SESSIONS]
    return [_public("codex", UNKNOWN_PROJECT, int(mtime), classify(now - mtime)) for mtime in recent]


class AiSessionsCollector:
    """Assemble la réponse de `/api/ai`."""

    def __init__(
        self,
        claude_dir: Path,
        codex_dir: Path,
        clock: Callable[[], float] = time.time,
        pid_alive: PidAlive | None = None,
    ):
        self._claude_dir = claude_dir
        self._codex_dir = codex_dir
        self._clock = clock
        self._pid_alive = pid_alive

    def collect(self, include_stale: bool = False) -> dict:
        now = self._clock()
        sessions = scan_claude(self._claude_dir, now, self._pid_alive) + scan_codex(self._codex_dir, now)
        if not include_stale:
            sessions = [s for s in sessions if s["state"] != "stale"]
        return {"sessions": sessions}

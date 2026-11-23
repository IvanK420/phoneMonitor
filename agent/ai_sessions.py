"""Sessions IA (Claude Code, Codex) — logique pure + lecture tolérante des fichiers de session.

Sécurité (04-securite-planning.md) : on ne renvoie jamais le contenu d'une session,
seulement outil, nom de projet, état et date. Les fichiers `*.key` ne sont jamais ouverts.
"""

import json
import re

UNKNOWN_PROJECT = "?"
_PATH_SEPARATORS = re.compile(r"[/\\]")
WORKING_UNDER_S = 10
STALE_FROM_S = 600

_EXPLICIT_STATES = {"busy": "working", "idle": "idle"}


def classify(age_s: float) -> str:
    """Heuristique v1 : modifié il y a < 10 s → working ; < 10 min → idle ; sinon stale."""
    if age_s < WORKING_UNDER_S:
        return "working"
    if age_s < STALE_FROM_S:
        return "idle"
    return "stale"


def session_state(status: object, age_s: float) -> str:
    """Le statut explicite (`busy` / `idle`) prime, sauf pour une session figée depuis 10 min."""
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
    return {
        "project": project_name(data.get("cwd")),
        "updated_at": int(max(stamps_ms) // 1000) if stamps_ms else int(mtime),
        "status": status if isinstance(status, str) else None,
    }

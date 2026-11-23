"""Sessions IA (Claude Code, Codex) — logique pure + lecture tolérante des fichiers de session.

Sécurité (04-securite-planning.md) : on ne renvoie jamais le contenu d'une session,
seulement outil, nom de projet, état et date. Les fichiers `*.key` ne sont jamais ouverts.
"""

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

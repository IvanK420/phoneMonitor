"""Vérification du jeton d'accès (04-securite-planning.md) : en-tête `X-Token` ou `?token=`."""

import hmac
from collections.abc import Callable

from fastapi import HTTPException, Request, status


def token_matches(given: object, expected: str) -> bool:
    """Comparaison en temps constant (pas de fuite de longueur de préfixe commun)."""
    if not isinstance(given, str) or not given:
        return False
    return hmac.compare_digest(given.encode("utf-8"), expected.encode("utf-8"))


def require_token(expected: str) -> Callable[[Request], None]:
    """Dépendance FastAPI : 401 sans jeton valide. Un en-tête présent est seul pris en compte."""

    def check(request: Request) -> None:
        given = request.headers.get("x-token")
        if given is None:
            given = request.query_params.get("token")
        if not token_matches(given, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="jeton manquant ou invalide")

    return check

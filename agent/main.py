"""Point d'entrée de l'agent PhoneBox Lite.

`create_app()` reçoit ses dépendances pour que les tests puissent injecter des fakes ;
le câblage des vraies sources se fait au lancement.
"""

import mimetypes
from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from agent.ai_sessions import AiSessionsCollector
from agent.auth import require_token
from agent.cache import TTLCache
from agent.claude_usage import UsageCollector, UsageTracker

StatsProvider = Callable[[], dict]
AiProvider = Callable[[bool], dict]  # include_stale -> {"sessions": [...]}
UsageProvider = Callable[[], dict]  # {"today", "window_5h", "hourly"}

USAGE_TTL_S = 10.0  # la consommation n'a pas besoin d'être plus fraîche

PANEL_DIR = Path(__file__).resolve().parent.parent / "panel"

# Le registre Windows peut associer .js à text/plain : les modules ES seraient refusés.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("application/manifest+json", ".webmanifest")


def default_ai_provider() -> AiProvider:
    import psutil  # vivacité des processus de session ; import tardif comme les autres sources

    home = Path.home()
    return AiSessionsCollector(
        claude_dir=home / ".claude" / "sessions",
        codex_dir=home / ".codex" / "sessions",
        pid_alive=psutil.pid_exists,
    ).collect


def default_usage_provider(ttl: float = USAGE_TTL_S) -> UsageProvider:
    """Transcriptions de ~/.claude/projects, relues au plus toutes les `ttl` secondes."""
    tracker = UsageTracker(Path.home() / ".claude" / "projects")
    return TTLCache(UsageCollector(tracker).collect, ttl=ttl)


def create_app(
    stats: StatsProvider | None = None,
    ai: AiProvider | None = None,
    usage: UsageProvider | None = None,
    token: str | None = None,
    oled: dict | None = None,
    panel_dir: Path = PANEL_DIR,
) -> FastAPI:
    oled = dict(oled or {})
    if stats is None:
        from agent.sources import build_stats_provider  # import tardif : les tests n'en ont pas besoin

        stats = build_stats_provider()
    if ai is None:
        ai = default_ai_provider()
    if usage is None:
        usage = default_usage_provider()
    if token is None:
        from agent.config import load_config

        config = load_config()
        token = config["token"]
        oled = oled or config.get("oled", {})

    # Pas de /docs ni /openapi.json : l'agent n'expose que ce dont le panneau a besoin.
    app = FastAPI(title="PhoneBox Lite", docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    # Lecture seule : uniquement des GET ; tout le reste répond 405.
    api = APIRouter(prefix="/api", dependencies=[Depends(require_token(token))])

    @api.get("/stats")
    def api_stats() -> dict:
        return stats()

    @api.get("/ai")
    def api_ai(include_stale: bool = False) -> dict:
        return ai(include_stale)

    @api.get("/usage")
    def api_usage() -> dict:
        return usage()

    @api.get("/config")
    def api_config() -> dict:
        # Uniquement les réglages d'affichage ; le panneau fusionne avec ses défauts (oled.js).
        return {"oled": oled}

    app.include_router(api)

    # Monté en dernier : les routes /api et /healthz restent prioritaires.
    app.mount("/", StaticFiles(directory=panel_dir, html=True), name="panel")

    return app

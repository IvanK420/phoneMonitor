"""Point d'entrée de l'agent PhoneBox Lite.

`create_app()` reçoit ses dépendances pour que les tests puissent injecter des fakes ;
le câblage des vraies sources se fait au lancement.
"""

import mimetypes
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from agent.ai_sessions import AiSessionsCollector

StatsProvider = Callable[[], dict]
AiProvider = Callable[[bool], dict]  # include_stale -> {"sessions": [...]}

PANEL_DIR = Path(__file__).resolve().parent.parent / "panel"

# Le registre Windows peut associer .js à text/plain : les modules ES seraient refusés.
mimetypes.add_type("text/javascript", ".js")


def default_ai_provider() -> AiProvider:
    import psutil  # vivacité des processus de session ; import tardif comme les autres sources

    home = Path.home()
    return AiSessionsCollector(
        claude_dir=home / ".claude" / "sessions",
        codex_dir=home / ".codex" / "sessions",
        pid_alive=psutil.pid_exists,
    ).collect


def create_app(
    stats: StatsProvider | None = None,
    ai: AiProvider | None = None,
    panel_dir: Path = PANEL_DIR,
) -> FastAPI:
    if stats is None:
        from agent.sources import build_stats_provider  # import tardif : les tests n'en ont pas besoin

        stats = build_stats_provider()
    if ai is None:
        ai = default_ai_provider()

    app = FastAPI(title="PhoneBox Lite")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    @app.get("/api/stats")
    def api_stats() -> dict:
        return stats()

    @app.get("/api/ai")
    def api_ai(include_stale: bool = False) -> dict:
        return ai(include_stale)

    # Monté en dernier : les routes /api et /healthz restent prioritaires.
    app.mount("/", StaticFiles(directory=panel_dir, html=True), name="panel")

    return app

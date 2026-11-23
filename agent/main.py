"""Point d'entrée de l'agent PhoneBox Lite.

`create_app()` reçoit ses dépendances pour que les tests puissent injecter des fakes ;
le câblage des vraies sources se fait au lancement.
"""

import mimetypes
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

StatsProvider = Callable[[], dict]

PANEL_DIR = Path(__file__).resolve().parent.parent / "panel"

# Le registre Windows peut associer .js à text/plain : les modules ES seraient refusés.
mimetypes.add_type("text/javascript", ".js")


def create_app(stats: StatsProvider | None = None, panel_dir: Path = PANEL_DIR) -> FastAPI:
    if stats is None:
        from agent.sources import build_stats_provider  # import tardif : les tests n'en ont pas besoin

        stats = build_stats_provider()

    app = FastAPI(title="PhoneBox Lite")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    @app.get("/api/stats")
    def api_stats() -> dict:
        return stats()

    # Monté en dernier : les routes /api et /healthz restent prioritaires.
    app.mount("/", StaticFiles(directory=panel_dir, html=True), name="panel")

    return app

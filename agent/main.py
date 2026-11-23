"""Point d'entrée de l'agent PhoneBox Lite.

`create_app()` reçoit ses dépendances pour que les tests puissent injecter des fakes ;
le câblage des vraies sources se fait au lancement.
"""

from collections.abc import Callable

from fastapi import FastAPI

StatsProvider = Callable[[], dict]


def create_app(stats: StatsProvider | None = None) -> FastAPI:
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

    return app

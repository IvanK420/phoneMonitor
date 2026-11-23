"""Point d'entrée de l'agent PhoneBox Lite.

`create_app()` reçoit ses dépendances pour que les tests puissent injecter des fakes ;
le câblage des vraies sources se fait au lancement.
"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="PhoneBox Lite")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    return app

"""Lancement : `python -m agent` → http://127.0.0.1:8765 (accès LAN et jeton : M4)."""

import uvicorn

from agent.main import create_app

HOST = "127.0.0.1"
PORT = 8765


def main() -> None:
    uvicorn.run(create_app(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()

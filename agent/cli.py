"""Options de lancement (`python -m agent [--lan] [--port N]`) et URL à ouvrir sur le téléphone."""

import argparse
from dataclasses import dataclass

LOCALHOST = "127.0.0.1"
ALL_INTERFACES = "0.0.0.0"
DEFAULT_PORT = 8765


@dataclass(frozen=True)
class Options:
    host: str
    port: int


def _port(value: str) -> int:
    port = int(value)  # ValueError → message d'argparse
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("le port doit être entre 1 et 65535")
    return port


def parse_args(argv: list[str] | None = None) -> Options:
    parser = argparse.ArgumentParser(prog="python -m agent", description="Agent PhoneBox Lite")
    parser.add_argument(
        "--lan",
        action="store_true",
        help="écouter sur le réseau local (0.0.0.0) au lieu de 127.0.0.1 uniquement",
    )
    parser.add_argument("--port", type=_port, default=DEFAULT_PORT, help=f"port d'écoute (défaut {DEFAULT_PORT})")
    args = parser.parse_args(argv)
    return Options(host=ALL_INTERFACES if args.lan else LOCALHOST, port=args.port)


def panel_urls(host: str, port: int, token: str, lan_ips: list[str]) -> list[str]:
    """URL(s) du panneau avec le jeton, à ouvrir une fois sur le téléphone (il le mémorise)."""
    hosts = lan_ips if host == ALL_INTERFACES and lan_ips else [LOCALHOST]
    return [f"http://{h}:{port}/?token={token}" for h in hosts]

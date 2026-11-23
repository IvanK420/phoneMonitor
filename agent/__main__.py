"""Lancement : `python -m agent` (127.0.0.1) ou `python -m agent --lan` (réseau local)."""

import socket
import sys

import psutil
import uvicorn

from agent.cli import parse_args, panel_urls
from agent.config import ConfigError, load_config
from agent.main import create_app


def lan_ipv4_addresses() -> list[str]:
    """Adresses IPv4 des interfaces actives, hors boucle locale et APIPA (169.254.x.x)."""
    stats = psutil.net_if_stats()
    ips = []
    for name, addrs in psutil.net_if_addrs().items():
        if name in stats and not stats[name].isup:
            continue
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith(("127.", "169.254.")):
                ips.append(addr.address)
    return ips


def main(argv: list[str] | None = None) -> None:
    options = parse_args(argv)
    try:
        config = load_config()
    except ConfigError as exc:
        sys.exit(f"Erreur de configuration : {exc}")

    print("\nPanneau PhoneBox Lite — ouvrir une fois sur le téléphone (le jeton est ensuite mémorisé) :")
    for url in panel_urls(options.host, options.port, config["token"], lan_ipv4_addresses()):
        print(f"  {url}")
    if options.host == "127.0.0.1":
        print("  (accès local uniquement : --lan pour le Wi-Fi, ou « adb reverse tcp:8765 tcp:8765 » en USB)")
    print()

    app = create_app(token=config["token"], oled=config.get("oled", {}))
    uvicorn.run(app, host=options.host, port=options.port)


if __name__ == "__main__":
    main()

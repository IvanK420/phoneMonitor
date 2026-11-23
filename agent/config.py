"""Configuration locale (`config.json`, ignoré par git) : jeton d'accès et réglages du panneau."""

import json
import secrets
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
MIN_TOKEN_LENGTH = 32


class ConfigError(RuntimeError):
    pass


def _valid_token(token: object) -> bool:
    return isinstance(token, str) and len(token) >= MIN_TOKEN_LENGTH


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Lit `config.json` ; au premier lancement (ou jeton absent / trop court), génère un jeton
    aléatoire et l'enregistre en conservant les autres réglages. Un fichier illisible n'est
    jamais écrasé : il peut contenir des réglages écrits à la main."""
    config: dict = {}
    if path.exists():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ConfigError(f"{path} n'est pas du JSON valide : corrigez-le ou supprimez-le") from exc
        if not isinstance(config, dict):
            raise ConfigError(f"{path} doit contenir un objet JSON")

    if not _valid_token(config.get("token")):
        config["token"] = secrets.token_urlsafe(32)  # 43 caractères
        path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return config

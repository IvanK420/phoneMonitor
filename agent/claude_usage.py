"""Consommation de tokens Claude Code, lue dans les transcriptions locales (~/.claude/projects/**/*.jsonl).

Confidentialité : seuls les compteurs numériques de `message.usage` et l'horodatage sont retenus.
Aucun contenu de conversation, chemin, identifiant de session ou nom de modèle ne sort d'ici.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class UsageRecord:
    key: str  # message.id/requestId : une réponse est écrite sur plusieurs lignes, à compter une fois
    ts: float
    input: int
    output: int
    cache_read: int
    cache_creation: int

    @property
    def total(self) -> int:
        return self.input + self.output + self.cache_read + self.cache_creation


def _count(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def _epoch(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


def parse_usage_line(line: str) -> UsageRecord | None:
    """Une ligne JSONL → compteurs de tokens, ou None si la ligne n'en porte pas (ou est inexploitable)."""
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    if not isinstance(entry, dict) or entry.get("type") != "assistant":
        return None
    message = entry.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("usage"), dict):
        return None

    ts = _epoch(entry.get("timestamp"))
    message_id, request_id = message.get("id"), entry.get("requestId")
    if ts is None or not isinstance(message_id, str) or not isinstance(request_id, str):
        return None

    usage = message["usage"]
    return UsageRecord(
        key=f"{message_id}/{request_id}",
        ts=ts,
        input=_count(usage.get("input_tokens")),
        output=_count(usage.get("output_tokens")),
        cache_read=_count(usage.get("cache_read_input_tokens")),
        cache_creation=_count(usage.get("cache_creation_input_tokens")),
    )


class UsageTracker:
    """Lit les transcriptions de façon incrémentale : seules les lignes ajoutées depuis la dernière
    lecture sont analysées, et seuls les fichiers modifiés dans la période sont ouverts."""

    def __init__(self, projects_dir: Path):
        self._dir = projects_dir
        self._offsets: dict[Path, int] = {}
        self._records: dict[str, UsageRecord] = {}

    def refresh(self, since: float) -> list[UsageRecord]:
        """Met à jour puis renvoie les relevés dont l'horodatage est >= `since`."""
        if self._dir.is_dir():
            for path in self._dir.rglob("*.jsonl"):
                try:
                    stat = path.stat()
                except OSError:
                    continue
                if stat.st_mtime >= since:
                    self._read_new_lines(path, stat.st_size)
        self._records = {k: r for k, r in self._records.items() if r.ts >= since}
        return list(self._records.values())

    def _read_new_lines(self, path: Path, size: int) -> None:
        offset = self._offsets.get(path, 0)
        if size < offset:  # fichier tronqué ou remplacé : on repart du début
            offset = 0
        if size == offset:
            return
        try:
            with path.open("rb") as f:
                f.seek(offset)
                data = f.read(size - offset)
        except OSError:
            return
        end = data.rfind(b"\n")
        if end < 0:  # ligne en cours d'écriture : on attend qu'elle soit complète
            self._offsets[path] = offset
            return
        self._offsets[path] = offset + end + 1
        for raw in data[: end + 1].splitlines():
            record = parse_usage_line(raw.decode("utf-8", errors="replace"))
            if record is not None:
                self._records[record.key] = record

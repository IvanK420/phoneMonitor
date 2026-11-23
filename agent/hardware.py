"""Collecte matériel — logique pure.

Les vraies sources (psutil, nvidia-smi) vivent dans `sources.py` ; ici on ne fait
que transformer leurs sorties en schéma `/api/stats` (voir 02-api.md).
"""

NVIDIA_SMI_QUERY = "name,utilization.gpu,memory.used,temperature.gpu"
_NVIDIA_FIELDS = 4


def _int_or_none(raw: str) -> int | None:
    try:
        return round(float(raw))
    except ValueError:  # "[N/A]", "[Not Supported]"…
        return None


def parse_nvidia_smi(text: str | None) -> dict | None:
    """Parse `nvidia-smi --query-gpu=<NVIDIA_SMI_QUERY> --format=csv,noheader,nounits`.

    Ne garde que le premier GPU. Toute sortie inexploitable (vide, erreur,
    commande absente) donne `None`.
    """
    if not text:
        return None
    for line in text.splitlines():
        fields = [f.strip() for f in line.split(",")]
        if len(fields) != _NVIDIA_FIELDS or not fields[0]:
            continue
        name, util, vram, temp = fields
        return {
            "name": name,
            "percent": _int_or_none(util),
            "vram_used_mb": _int_or_none(vram),
            "temp_c": _int_or_none(temp),
        }
    return None

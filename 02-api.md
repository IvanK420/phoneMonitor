# 02 — API de l'agent

Base : `http://<ip-du-pc>:8765`. Tous les endpoints (sauf `/healthz`) exigent le jeton : en-tête `X-Token` ou paramètre `?token=`.

## `GET /healthz`
Retourne `{"ok": true}`.

## `GET /api/stats`

```json
{
  "ts": 1731672000,
  "cpu": { "percent": 23.5, "temp_c": 58 },
  "ram": { "used_gb": 11.2, "total_gb": 32, "percent": 35 },
  "gpu": { "name": "RTX 4070", "percent": 12, "vram_used_mb": 2100, "temp_c": 49 },
  "disks": [ { "mount": "C:", "used_gb": 410, "total_gb": 953 } ],
  "net": { "down_kbps": 1200, "up_kbps": 85 }
}
```

`gpu` et `temp_c` sont `null` si indisponibles.

## `GET /api/ai`

```json
{
  "sessions": [
    {
      "tool": "claude-code",
      "project": "mon-projet",
      "state": "working",
      "updated_at": 1731671990
    }
  ]
}
```

### États d'une session

| État | Règle heuristique (v1) |
|---|---|
| `working` | fichier de session modifié il y a moins de 10 s |
| `idle` | modifié il y a moins de 10 min |
| `stale` | plus ancien : masqué par défaut |

> Les formats de fichiers de session ne sont pas documentés : inspecter les dossiers réels avant de coder le parseur. Prévoir une version tolérante (si le parsing échoue, on retombe sur la date de modification).

## Statique

`GET /` sert le panneau (`panel/index.html`).

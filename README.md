# PhoneBox Lite — Dossier de conception

Version réduite de [PhoneBox](https://github.com/ersinkoc/phonebox) : un vieux téléphone Android devient un panneau de bureau affichant **le matériel du PC** et **l'activité des sessions IA**.

## Périmètre

| Inclus (v1) | Exclu (v1) |
|---|---|
| Stats CPU / RAM / GPU / disques / réseau | Éditeur de mise en page |
| Liste des sessions IA (Claude Code, Codex) | Règles et webhooks |
| Panneau web plein écran | Application Android native |
| Jeton d'accès simple | Mises à jour automatiques |

## Documents

1. [01-architecture.md](01-architecture.md) — composants et flux
2. [02-api.md](02-api.md) — endpoints de l'agent
3. [03-interface.md](03-interface.md) — panneau et widgets
4. [04-securite-planning.md](04-securite-planning.md) — sécurité, risques, jalons
5. [05-plan-tdd.md](05-plan-tdd.md) — plan d'implémentation en TDD adapté

## Lancer

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\python -m agent          # 127.0.0.1:8765 uniquement
.\.venv\Scripts\python -m agent --lan    # accessible depuis le Wi-Fi local
```

Au premier lancement, l'agent crée `config.json` (ignoré par git) avec un jeton aléatoire, puis affiche l'URL du panneau
avec ce jeton. Ouvrez-la **une fois** sur le téléphone : le jeton est mémorisé puis retiré de la barre d'adresse.

**Téléphone en USB** (débogage USB activé) : `adb reverse tcp:8765 tcp:8765`, puis ouvrir `http://localhost:8765/?token=…`
sur le téléphone. C'est aussi le seul mode où le maintien de l'écran (Wake Lock) fonctionne : le navigateur ne l'autorise
qu'en contexte sécurisé (`localhost` ou HTTPS).

**Téléphone en Wi-Fi** (`--lan`) : en `http://<ip-du-pc>`, Wake Lock est indisponible. Activer *Options pour les
développeurs → Rester activé* : l'écran reste allumé tant que le téléphone charge.

Réglages OLED facultatifs dans `config.json` (valeurs par défaut du doc 03) :

```json
{ "oled": { "pixel_shift": true, "shift_interval_s": 90, "night_start": "23:00", "night_end": "07:00",
            "night_brightness": 0.1, "swap_minutes": 0 } }
```

Tests : `.\run-tests.ps1` (ajouter `-System` pour les tests sur les vraies sources).

## Stack recommandée

- **Agent** : Python 3.11+, FastAPI, `psutil` (alternative : Node + `systeminformation`)
- **Panneau** : HTML + JS vanilla (ou Chart.js), sans build
- **GPU NVIDIA** : appel à `nvidia-smi`

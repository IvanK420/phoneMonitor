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

## Stack recommandée

- **Agent** : Python 3.11+, FastAPI, `psutil` (alternative : Node + `systeminformation`)
- **Panneau** : HTML + JS vanilla (ou Chart.js), sans build
- **GPU NVIDIA** : appel à `nvidia-smi`

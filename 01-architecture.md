# 01 — Architecture

## Vue d'ensemble

```
┌─────────────── PC ───────────────┐          ┌──── Téléphone ────┐
│  Agent (FastAPI)                 │          │  Navigateur       │
│  ├─ collecteur matériel (psutil) │  HTTP    │  plein écran      │
│  ├─ collecteur IA (fichiers)     │◄────────►│  panneau HTML/JS  │
│  └─ serveur statique (panneau)   │  Wi-Fi   │  (sondage 2 s)    │
└──────────────────────────────────┘          └───────────────────┘
```

## Composants

| Composant | Rôle |
|---|---|
| **Collecteur matériel** | Lit CPU, RAM, disques, réseau (`psutil`) et GPU (`nvidia-smi`) |
| **Collecteur IA** | Parcourt `~/.claude/sessions` et `~/.codex/sessions`, déduit l'état de chaque session |
| **API HTTP** | Expose le tout en JSON (voir `02-api.md`) |
| **Panneau** | Page statique qui interroge l'API et dessine les widgets |

## Principes

- **Local d'abord** : aucun cloud, aucune dépendance externe.
- **Échantillonnage à la demande** : on ne mesure que lorsqu'un client interroge, avec un cache de 1 s.
- **Tolérance aux pannes** : si une source manque (pas de GPU, pas de dossier Codex), le widget correspondant s'efface, l'agent ne plante pas.

## Arborescence proposée

```
phonebox-lite/
├─ agent/
│  ├─ main.py        # app FastAPI
│  ├─ hardware.py    # collecte matériel
│  ├─ ai_sessions.py # collecte sessions IA
│  └─ config.py      # port, jeton, intervalle
└─ panel/
   ├─ index.html
   ├─ app.js
   └─ style.css
```

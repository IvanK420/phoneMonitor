# 04 — Sécurité, risques et planning

## Sécurité

| Sujet | Décision |
|---|---|
| Écoute réseau | `127.0.0.1` par défaut ; accès LAN activé explicitement (`--lan`) |
| Authentification | Jeton aléatoire généré au premier lancement, stocké dans `config.json` |
| Transport | HTTP en LAN domestique acceptable ; HTTPS ou Tailscale si le réseau n'est pas de confiance |
| Données exposées | Lecture seule : aucune commande n'est exécutable depuis le téléphone |
| Chemins IA | Ne jamais renvoyer le contenu des sessions, seulement nom de projet et état |

## Risques

| Risque | Impact | Parade |
|---|---|---|
| Format des sessions IA non documenté | Widget IA cassé après une mise à jour | Parseur tolérant + repli sur la date de modification |
| Quotas IA via endpoint non documenté | Fragile | Hors v1, à traiter comme option |
| GPU non NVIDIA | Pas de stats GPU | Widget masqué ; support AMD/Intel en v2 |
| Écran allumé en continu | Brûlure OLED | Thème sombre, légère rotation de position, veille nocturne |
| Réseau Wi-Fi coupé | Panneau figé | Indicateur hors ligne + reconnexion auto |

## Jalons

| # | Jalon | Livrable | Durée estimée |
|---|---|---|---|
| M1 | Agent matériel | `/api/stats` fonctionnel | 0,5 jour |
| M2 | Panneau | Page avec 4 widgets matériel | 1 jour |
| M3 | Sessions IA | `/api/ai` + widget | 1 jour |
| M4 | Finitions | Jeton, plein écran, Wake Lock, indicateur hors ligne | 0,5 jour |
| M5 *(option)* | App Android | WebView + `adb reverse` pour l'USB | 1 semaine |

## Critères d'acceptation v1

- Le panneau s'affiche sur le téléphone en moins de 3 s.
- Les valeurs se rafraîchissent toutes les 2 s sans fuite mémoire sur 24 h.
- L'agent consomme moins de 2 % de CPU au repos.
- Sans jeton valide, l'API répond 401.

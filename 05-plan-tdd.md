# 05 — Plan d'implémentation (TDD adapté)

## Philosophie : « TDD là où ça paie »

Le TDD strict (rouge → vert → refactor) s'applique à toute la **logique pure**. Les frontières avec le monde extérieur (`psutil`, `nvidia-smi`, système de fichiers, API navigateur) sont **isolées derrière de fines couches injectables**, testées par contrat ou à la main.

| Couche | Approche | Outil |
|---|---|---|
| Logique pure Python (calculs, heuristiques, parsing, config) | **TDD strict** | `pytest` |
| Adaptateurs système (`psutil`, `nvidia-smi`, FS) | Fakes injectés + tests sur **sorties capturées** (fixtures) | `pytest`, `tmp_path`, `monkeypatch` |
| API HTTP | Tests d'intégration écrits **avant** l'endpoint | `fastapi.testclient` / `httpx` |
| Logique pure JS (seuils, formatage, sparkline, horaires OLED) | **TDD strict** | `node --test` (Node 24 natif, aucun build) |
| DOM, Wake Lock, plein écran, rendu visuel | Checklist manuelle sur le téléphone | — |
| Critères non fonctionnels (CPU < 2 %, 24 h sans fuite) | Scripts de mesure, pas de TDD | script `bench/` |

Règle de base : **le code qui décide est pur et testé ; le code qui touche le monde est mince et bête.**

## Arborescence cible (ajouts au doc 01)

```
phonebox-lite/
├─ agent/
│  ├─ main.py           # create_app(config, collectors) → app FastAPI
│  ├─ config.py         # chargement / génération jeton
│  ├─ auth.py           # dépendance FastAPI de vérification du jeton
│  ├─ cache.py          # TTLCache(1 s, horloge injectable)
│  ├─ hardware.py       # collect_stats(sources) — pur
│  ├─ sources.py        # adaptateurs psutil / nvidia-smi (minces)
│  ├─ ai_sessions.py    # scan + parseurs + heuristique d'état
│  └─ net_rate.py       # débit réseau à partir de deux compteurs
├─ panel/
│  ├─ index.html, style.css, app.js     # app.js = colle DOM uniquement
│  └─ lib/
│     ├─ thresholds.js  # niveau vert / orange / rouge
│     ├─ format.js      # Go, kbps → libellés
│     ├─ ring.js        # tampon circulaire 60 points (sparkline)
│     ├─ poller.js      # sondage + compteur d'échecs → hors ligne
│     └─ oled.js        # pixel shift, plage nocturne, permutation
└─ tests/
   ├─ agent/            # pytest
   ├─ panel/            # *.test.js (node --test)
   └─ fixtures/         # sorties nvidia-smi, sessions anonymisées
```

Point clé de conception : `create_app()` reçoit ses dépendances (config, collecteurs, horloge). Les tests construisent l'app avec des fakes ; `main.py` câble les vrais.

---

## Étape 0 — Squelette et outillage (≈ 1 h)

1. `pyproject.toml` : `fastapi`, `uvicorn`, `psutil` ; dev : `pytest`, `httpx`.
2. Premier test **rouge** : `GET /healthz` → `200 {"ok": true}`. Implémenter → vert.
3. `node --test tests/panel` avec un test trivial pour valider la chaîne.
4. Script unique `run-tests` (pytest + node --test).

**Fini quand** : les deux suites tournent d'une commande.

---

## M1 — Agent matériel (`/api/stats`)

Ordre des cycles TDD :

| # | Test (écrit d'abord) | Implémentation |
|---|---|---|
| 1.1 | `TTLCache` : deux appels à < 1 s → une seule mesure ; à 1,1 s → nouvelle mesure (horloge fake) | `cache.py` |
| 1.2 | `net_rate(prev, cur, dt)` → `down_kbps`, `up_kbps` ; `dt = 0` ou compteur qui recule → 0, jamais négatif | `net_rate.py` |
| 1.3 | `parse_nvidia_smi(texte_csv)` sur fixtures : 1 GPU, sortie vide, « command not found », valeurs `[N/A]` → `None` | `hardware.py` |
| 1.4 | `collect_stats(sources_fake)` produit exactement le schéma de `02-api.md` (Go arrondis, `percent`) | `hardware.py` |
| 1.5 | Source GPU absente / lève une exception → `gpu: null`, pas d'erreur | idem |
| 1.6 | Température indisponible (cas **Windows** : `psutil.sensors_temperatures` n'existe pas) → `temp_c: null` | idem |
| 1.7 | Disques : volumes inaccessibles (lecteur CD vide) ignorés sans planter | idem |
| 1.8 | Intégration : `GET /api/stats` avec collecteur fake → JSON conforme | `main.py` |

Puis, hors TDD : `sources.py` (vrais appels `psutil` / `subprocess`), vérifié par **un test « smoke »** marqué `@pytest.mark.system` qui appelle les vraies sources et vérifie seulement les types.

> Note environnement : pas de `nvidia-smi` sur ce PC → la fixture « command not found » est le cas réel ; capturer une vraie sortie CSV sur une machine NVIDIA pour la fixture positive (ou utiliser l'exemple documenté).

**Fini quand** : `curl localhost:8765/api/stats` renvoie des valeurs réelles, suite verte.

---

## M2 — Panneau (4 widgets matériel)

TDD sur les modules `panel/lib/*.js` (ES modules, importés tels quels par le navigateur et par Node) :

| # | Test | Module |
|---|---|---|
| 2.1 | `level(69.9) → "ok"`, `level(70) → "warn"`, `level(90) → "warn"`, `level(90.1) → "crit"` (bornes du doc 03 à figer) | `thresholds.js` |
| 2.2 | `formatGb(11.24) → "11,2 Go"`, `formatRate(1200) → "1,2 Mb/s"`, `null → "—"` | `format.js` |
| 2.3 | Tampon circulaire : capacité 60, l'ajout du 61ᵉ éjecte le 1ᵉʳ ; `toPath(w, h)` produit un chemin SVG normalisé | `ring.js` |
| 2.4 | `Poller` avec `fetch` et timers fakes : succès → `onData` ; 3 échecs consécutifs → `offline = true` ; un succès → retour en ligne | `poller.js` |
| 2.5 | `viewModel(stats)` : `gpu: null` → widget GPU `hidden` | `app-model.js` |

Hors TDD : `index.html`, `style.css`, rendu des jauges SVG, grille 3×2. Vérification manuelle (checklist M2 ci-dessous) dans le navigateur desktop puis sur le téléphone.

**Checklist manuelle M2** : paysage sans défilement · jauges qui bougent · GPU masqué sur ce PC · coupure de l'agent → « hors ligne » après ~6 s.

---

## M3 — Sessions IA (`/api/ai` + widget)

### Spike préalable (fait pendant la planification)

Inspection de `~/.claude/sessions/` sur ce PC :

- `<pid>.json` : champs utiles `cwd`, `status` (`busy` / `idle` observés), `updatedAt` et `statusUpdatedAt` (**millisecondes**), `name`.
- `<pid>.<hash>.key` : **secrets — ne jamais lire ni exposer**. Le scanner ne doit ouvrir que `*.json`.
- `~/.codex/sessions` : absent sur ce PC → cas « dossier manquant » réel.

Créer des fixtures **anonymisées** (cwd, ids factices) à partir de ce format.

### Cycles TDD

| # | Test | Notes |
|---|---|---|
| 3.1 | `classify(age_s)` : 9 s → `working`, 10 s → `idle`, 599 s → `idle`, 600 s → `stale` | heuristique du doc 02 |
| 3.2 | `parse_claude(json)` → `project = basename(cwd)`, `updated_at` en **secondes** | conversion ms → s |
| 3.3 | Champ `status: "busy"` présent → `working` même si l'heuristique dit `idle` (le statut explicite prime) | amélioration de la v1 |
| 3.4 | JSON corrompu / champs manquants → **repli sur mtime** du fichier, projet = `"?"` | parseur tolérant |
| 3.5 | `scan(dir)` ignore les `.key` et tout fichier non `.json` | sécurité |
| 3.6 | Dossier inexistant → liste vide, pas d'exception | Codex absent |
| 3.7 | Sortie ne contient **que** `tool, project, state, updated_at` (test de non‑fuite : pas de `cwd` complet, `sessionId`, `messagingSocketPath`…) | doc 04 |
| 3.8 | `stale` exclu par défaut ; `?include_stale=1` les inclut | |
| 3.9 | Codex : parseur générique basé sur mtime (format inconnu) ; à affiner quand un vrai dossier existe | |
| 3.10 | Intégration `GET /api/ai` avec `tmp_path` peuplé de fixtures | |
| 3.11 (JS) | `sessionBadge(state)` → classe couleur ; tri `working` d'abord puis par `updated_at` décroissant | `panel/lib` |

**Fini quand** : le widget liste les sessions réelles de ce PC avec la bonne pastille.

---

## M4 — Finitions (sécurité + navigateur + OLED)

### Sécurité (TDD strict, c'est le critère « 401 »)

| # | Test |
|---|---|
| 4.1 | Premier lancement sans `config.json` → fichier créé avec jeton aléatoire ≥ 32 car. ; second lancement → même jeton |
| 4.2 | `/api/*` sans jeton → 401 ; mauvais jeton → 401 ; `X-Token` valide → 200 ; `?token=` valide → 200 |
| 4.3 | `/healthz` sans jeton → 200 |
| 4.4 | Comparaison en temps constant (`hmac.compare_digest`) — test unitaire sur la fonction |
| 4.5 | Hôte d'écoute : défaut `127.0.0.1` ; `--lan` → `0.0.0.0` (test de la fonction de parsing des arguments) |
| 4.6 | Méthodes autres que `GET` sur `/api/*` → 405 (lecture seule) |

### OLED (`panel/lib/oled.js`, TDD sur la logique temporelle)

| # | Test |
|---|---|
| 4.7 | `shiftStep(i)` parcourt l'orbite de 9 positions, amplitude ≤ 3 px |
| 4.8 | `isNight("23:30", "23:00", "07:00") → true`, `"12:00" → false`, plage qui **traverse minuit** et plage simple |
| 4.9 | `screenMode({night, offlineSince, now})` → `normal` / `dim` / `black` (agent injoignable > 5 min → `black`) |
| 4.10 | `pickSwap(tiles, rng)` choisit 2 tuiles **de même taille** ; `swap_minutes = 0` → jamais ; alerte active ou interaction → suspendu |
| 4.11 | Fusion config : valeurs par défaut du doc 03 + surcharge partielle |

### Manuel (APIs navigateur, non testables utilement en unitaire)

- Wake Lock acquis, et **réacquis** après `visibilitychange` (piège classique).
- Bouton plein écran au premier toucher.
- Manifest PWA : ajout à l'écran d'accueil, barre masquée.
- Transition du pixel shift imperceptible (régler `shift_interval_s` à 5 s pour vérifier, puis remettre).

---

## Critères d'acceptation v1 → vérification

| Critère | Méthode |
|---|---|
| Affichage < 3 s | Mesure manuelle sur le téléphone (onglet Performance si débogage USB) |
| Rafraîchissement 2 s sans fuite sur 24 h | Panneau ouvert 24 h ; relever la mémoire JS (`performance.memory` / DevTools distant) au début et à la fin. Garde-fou testé : tampon sparkline borné (2.3), aucun `setInterval` créé dans la boucle de rendu |
| Agent < 2 % CPU au repos | Script `bench/idle_cpu.py` : lance l'agent, interroge à 2 s pendant 10 min, mesure le process via `psutil` |
| 401 sans jeton | Tests 4.2 (automatisés) |

## Ordre de travail et rythme

1. Étape 0 → M1 → M2 → M3 → M4, chaque jalon livrable et démontrable.
2. Chaque cycle : **un** test rouge → code minimal → refactor → commit (`test:` puis `feat:` ou commit unique par cycle).
3. Initialiser un dépôt git dès l'étape 0 (le dossier n'en est pas un aujourd'hui) et ajouter `config.json` au `.gitignore` (il contient le jeton).
4. Les tests `@pytest.mark.system` (vraies sources) sont exclus par défaut et lancés avant chaque fin de jalon.

## Points ouverts à trancher

- **Seuils exacts** : 70 % et 90 % sont-ils inclusifs côté « élevé » ? (proposé : `< 70` ok, `70–90` warn, `> 90` crit).
- **Statut explicite vs heuristique** pour Claude (test 3.3) : on fait confiance à `status: busy` ? (proposé : oui, avec repli heuristique).
- **Nom de projet** : `basename(cwd)` ou le champ `name` de la session ? (proposé : `basename(cwd)`, `name` en info-bulle éventuelle — à vérifier côté confidentialité).

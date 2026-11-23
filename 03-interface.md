# 03 — Interface du panneau

## Principes

- Thème **sombre**, contraste élevé (économie d'énergie sur écran OLED).
- Une seule page, orientation **paysage**.
- Aucun défilement : tout tient à l'écran.
- Sondage toutes les **2 s** ; indicateur « hors ligne » si 3 échecs d'affilée.

## Disposition (grille 3 × 2)

```
┌──────────┬──────────┬──────────┐
│   CPU    │   RAM    │   GPU    │
│  jauge   │  jauge   │  jauge   │
├──────────┴──────┬───┴──────────┤
│  Réseau         │  Sessions IA │
│  (sparkline)    │  (liste)     │
└─────────────────┴──────────────┘
         Disques (barres, bandeau bas)
```

## Widgets

| Widget | Données | Affichage |
|---|---|---|
| CPU | `cpu.percent`, `temp_c` | jauge circulaire + température |
| RAM | `ram.percent`, Go | jauge circulaire |
| GPU | `gpu.percent`, VRAM, temp | jauge ; masqué si `null` |
| Réseau | `down_kbps`, `up_kbps` | sparkline sur 60 points |
| Sessions IA | liste `sessions` | pastille couleur par état + projet |
| Disques | `disks[]` | barres horizontales |

## Couleurs d'état

- Vert : normal (< 70 %)
- Orange : élevé (70–90 %)
- Rouge : critique (> 90 %)
- Sessions : bleu = `working`, gris = `idle`

## Comportements navigateur

- **Wake Lock API** (`navigator.wakeLock`) pour garder l'écran allumé.
- **Plein écran** via un bouton au premier toucher (exigence des navigateurs).
- Ajout à l'écran d'accueil (PWA simple) pour masquer la barre d'adresse.

## Protection OLED

> Concerne uniquement les écrans OLED/AMOLED. Sur un écran LCD, ces mesures sont facultatives. Les trois premières sont activées par défaut ; la permutation de tuiles est désactivée par défaut.

### 1. Fond noir pur
- Fond `#000` partout, aucun dégradé de fond.
- Un pixel éteint ne s'use pas : c'est la mesure la plus efficace.

### 2. Décalage de pixels (pixel shifting)
- Tout le contenu est décalé de **1 à 3 px**, en orbite lente (haut → droite → bas → gauche).
- Fréquence : toutes les **1 à 2 minutes**, par transition CSS de 2 s (imperceptible).
- Implémentation : un conteneur racine avec `transform: translate(var(--dx), var(--dy))`.

```js
const steps = [[0,0],[2,0],[2,2],[0,2],[-2,2],[-2,0],[-2,-2],[0,-2],[2,-2]];
let i = 0;
setInterval(() => {
  const [dx, dy] = steps[i++ % steps.length];
  root.style.setProperty('--dx', dx + 'px');
  root.style.setProperty('--dy', dy + 'px');
}, 90_000);
```

### 3. Luminosité et couleurs
- Texte principal en gris clair (`#d0d0d0`), pas en blanc pur.
- Couleurs saturées réservées aux états d'alerte (orange, rouge).
- Éléments fixes (contours, libellés) en faible contraste.

### 4. Veille et atténuation
| Condition | Action |
|---|---|
| Plage nocturne configurée (ex. 23:00–07:00) | Panneau atténué à 10 % ou écran noir |
| Agent injoignable depuis plus de 5 min | Écran noir avec petit message décalé |
| PC en veille ou verrouillé | Atténuation progressive |

### 5. Permutation de tuiles (option, désactivée par défaut)
- Intervalle : **15 à 30 minutes**.
- Échange de **2 tuiles de même taille** à la fois (jamais de réorganisation complète).
- Animation FLIP : mesure des positions, application d'un `transform` inverse, puis transition de 600 ms.
- Suspendue pendant une interaction tactile et pendant une alerte active.
- Réglage : `oled.swap_minutes` (0 = désactivé).

### Réglages exposés (`config.json`)

```json
{
  "oled": {
    "pixel_shift": true,
    "shift_interval_s": 90,
    "night_start": "23:00",
    "night_end": "07:00",
    "night_brightness": 0.1,
    "swap_minutes": 0
  }
}
```

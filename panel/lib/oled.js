// Protection OLED (03-interface.md) : logique temporelle pure, appliquée au DOM par app.js.

// Réglages exposés dans config.json → "oled".
export const OLED_DEFAULTS = Object.freeze({
  pixel_shift: true,
  shift_interval_s: 90,
  night_start: '23:00',
  night_end: '07:00',
  night_brightness: 0.1,
  swap_minutes: 0,
});

// --- Décalage de pixels : orbite lente de 9 positions, amplitude 2 px -------------------
const ORBIT = [
  [0, 0],
  [2, 0],
  [2, 2],
  [0, 2],
  [-2, 2],
  [-2, 0],
  [-2, -2],
  [0, -2],
  [2, -2],
];

export function shiftStep(i) {
  const n = ORBIT.length;
  const k = ((Math.trunc(i) % n) + n) % n;
  return [...ORBIT[k]];
}

// --- Plage nocturne ------------------------------------------------------------------
const HHMM = /^([01]\d|2[0-3]):([0-5]\d)$/;

function minutes(hhmm) {
  const m = typeof hhmm === 'string' ? HHMM.exec(hhmm) : null;
  return m ? Number(m[1]) * 60 + Number(m[2]) : null;
}

export const toHHMM = (date) =>
  `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;

// Début inclus, fin exclue ; une plage dont la fin précède le début traverse minuit.
export function isNight(time, start, end) {
  const [t, s, e] = [minutes(time), minutes(start), minutes(end)];
  if (t === null || s === null || e === null || s === e) return false;
  return s < e ? t >= s && t < e : t >= s || t < e;
}

// --- Mode d'écran ----------------------------------------------------------------------
export const BLACK_AFTER_MS = 5 * 60_000;

export function screenMode({ night, offlineSince, now }) {
  if (offlineSince !== null && offlineSince !== undefined && now - offlineSince > BLACK_AFTER_MS) return 'black';
  return night ? 'dim' : 'normal';
}

// --- Permutation de tuiles (option, désactivée par défaut) -----------------------------
// Renvoie deux identifiants de tuiles de même taille, ou null si rien à faire.
export function pickSwap(tiles, rng, { swapMinutes, alertActive = false, interacting = false }) {
  if (!(swapMinutes > 0) || alertActive || interacting) return null;
  const bySize = new Map();
  for (const t of tiles) bySize.set(t.size, [...(bySize.get(t.size) ?? []), t.id]);
  const candidates = [...bySize.values()].filter((ids) => ids.length >= 2).flat();
  if (candidates.length === 0) return null;

  const pick = (list) => list[Math.min(list.length - 1, Math.floor(rng() * list.length))];
  const first = pick(candidates);
  const size = tiles.find((t) => t.id === first).size;
  const second = pick(bySize.get(size).filter((id) => id !== first));
  return [first, second];
}

// --- Fusion de la configuration --------------------------------------------------------
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

const RULES = {
  pixel_shift: (v) => (typeof v === 'boolean' ? v : undefined),
  shift_interval_s: (v) => (isNum(v) ? Math.max(5, v) : undefined),
  night_start: (v) => (minutes(v) !== null ? v : undefined),
  night_end: (v) => (minutes(v) !== null ? v : undefined),
  night_brightness: (v) => (isNum(v) ? clamp(v, 0, 1) : undefined),
  swap_minutes: (v) => (isNum(v) ? Math.max(0, v) : undefined),
};

// Défauts du doc 03 + surcharge partielle ; clés inconnues et valeurs invalides ignorées.
export function mergeOledConfig(partial) {
  const merged = { ...OLED_DEFAULTS };
  if (!partial || typeof partial !== 'object') return merged;
  for (const [key, rule] of Object.entries(RULES)) {
    const value = rule(partial[key]);
    if (value !== undefined) merged[key] = value;
  }
  return merged;
}

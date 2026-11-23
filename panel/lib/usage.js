// Consommation de tokens Claude (réponse de /api/usage) → libellés et courbe horaire.
import { formatPercent, formatTokens, MISSING } from './format.js';

const HOURS = 24;
const round1 = (n) => Math.round(n * 10) / 10;
const isCount = (v) => typeof v === 'number' && Number.isFinite(v) && v >= 0;

function hours(hourly) {
  return Array.isArray(hourly) && hourly.length === HOURS && hourly.every(isCount) ? hourly : new Array(HOURS).fill(0);
}

export function usageModel(usage) {
  const today = usage?.today && typeof usage.today === 'object' ? usage.today : {};
  const window = usage?.window_5h && typeof usage.window_5h === 'object' ? usage.window_5h : {};
  const total = isCount(today.total) ? today.total : null;
  return {
    today: formatTokens(total),
    window: formatTokens(isCount(window.total) ? window.total : null),
    output: formatTokens(isCount(today.output) ? today.output : null),
    // Le cache relu à chaque échange domine le total : on l'affiche pour que le chiffre reste lisible.
    cacheShare: total > 0 && isCount(today.cache_read) ? formatPercent((today.cache_read / total) * 100) : MISSING,
    hourly: hours(usage?.hourly),
    empty: !(total > 0),
  };
}

// Barres verticales (une par heure) dans une boîte w × h ; la plus haute touche le haut.
export function hourlyBarsPath(hourly, w, h) {
  const max = hourly.reduce((m, v) => Math.max(m, v), 0);
  if (hourly.length === 0 || max <= 0) return '';
  const step = w / hourly.length;
  return hourly
    .map((v, i) => {
      if (!(v > 0)) return null;
      const height = Math.max(1, (v / max) * h); // une petite heure reste visible
      const [x1, x2, y] = [round1(i * step + 1), round1((i + 1) * step - 1), round1(h - height)];
      return `M${x1},${h}V${y}H${x2}V${h}Z`;
    })
    .filter(Boolean)
    .join(' ');
}

// Libellés affichés par le panneau (français : virgule décimale, espace des milliers).
// Formatage manuel plutôt qu'Intl : sortie identique sous Node et sur n'importe quel navigateur.
export const MISSING = '—';

const isMissing = (v) => typeof v !== 'number' || Number.isNaN(v);

function num(value, decimals) {
  const [int, frac] = value.toFixed(decimals).split('.');
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return frac === undefined ? grouped : `${grouped},${frac}`;
}

// Un chiffre après la virgule sous 100, entier au-delà.
const compact = (v) => num(v, v < 100 ? 1 : 0);

// Les volumes de l'agent sont en Gio (1024³) ; au-delà de 1000, on passe en Tio.
export function formatGb(gb) {
  if (isMissing(gb)) return MISSING;
  return gb >= 1000 ? `${compact(gb / 1024)} To` : `${compact(gb)} Go`;
}

// « 12,0 / 15,6 Go » : l'unité n'est répétée que si elle diffère (« 900 Go / 1,8 To »).
export function formatUsedTotal(usedGb, totalGb) {
  const used = formatGb(usedGb);
  const total = formatGb(totalGb);
  const unit = total.slice(total.lastIndexOf(' '));
  return used.endsWith(unit) ? `${used.slice(0, -unit.length)} / ${total}` : `${used} / ${total}`;
}

// Débits en kilobits/s (unités décimales, comme les débits réseau).
export function formatRate(kbps) {
  if (isMissing(kbps)) return MISSING;
  if (kbps >= 1_000_000) return `${compact(kbps / 1_000_000)} Gb/s`;
  if (kbps >= 1000) return `${compact(kbps / 1000)} Mb/s`;
  return `${num(kbps, 0)} kb/s`;
}

// Nombres de tokens (unités décimales) : 714 · 1,2 k · 337 k · 63,8 M · 1,5 G.
const TOKEN_UNITS = [
  [1e3, 'k'],
  [1e6, 'M'],
  [1e9, 'G'],
];

export function formatTokens(n) {
  if (isMissing(n)) return MISSING;
  if (n < 999.5) return num(n, 0);
  for (const [size, unit] of TOKEN_UNITS) {
    const x = n / size;
    // On passe à l'unité suivante plutôt que d'afficher « 1000 k ».
    if (x < 999.5 || unit === 'G') return `${num(x, x < 99.95 ? 1 : 0)} ${unit}`;
  }
  return MISSING; // inatteignable
}

export const formatPercent =(p) => (isMissing(p) ? MISSING : `${num(p, 0)} %`);
export const formatTemp = (c) => (isMissing(c) ? MISSING : `${num(c, 0)} °C`);
export const formatMb = (mb) => (isMissing(mb) ? MISSING : `${num(mb, 0)} Mo`);

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

// Débits en kilobits/s (unités décimales, comme les débits réseau).
export function formatRate(kbps) {
  if (isMissing(kbps)) return MISSING;
  if (kbps >= 1_000_000) return `${compact(kbps / 1_000_000)} Gb/s`;
  if (kbps >= 1000) return `${compact(kbps / 1000)} Mb/s`;
  return `${num(kbps, 0)} kb/s`;
}

export const formatPercent = (p) => (isMissing(p) ? MISSING : `${num(p, 0)} %`);
export const formatTemp = (c) => (isMissing(c) ? MISSING : `${num(c, 0)} °C`);
export const formatMb = (mb) => (isMissing(mb) ? MISSING : `${num(mb, 0)} Mo`);

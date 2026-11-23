// Niveau d'alerte d'un pourcentage (03-interface.md, « Couleurs d'état »).
// < 70 → ok (vert) · 70–90 inclus → warn (orange) · > 90 → crit (rouge).
export const WARN_AT = 70;
export const CRIT_ABOVE = 90;

export function level(percent) {
  if (typeof percent !== 'number' || Number.isNaN(percent)) return 'unknown';
  if (percent > CRIT_ABOVE) return 'crit';
  if (percent >= WARN_AT) return 'warn';
  return 'ok';
}

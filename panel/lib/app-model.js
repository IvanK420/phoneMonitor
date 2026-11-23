// Transforme la réponse de /api/stats en tout ce que le DOM affiche.
// app.js ne fait plus que recopier ces valeurs dans les éléments : aucune décision côté DOM.
import { level } from './thresholds.js';
import { formatMb, formatPercent, formatRate, formatTemp, formatUsedTotal } from './format.js';

const round1 = (n) => Math.round(n * 10) / 10;
const present = (v) => typeof v === 'number' && !Number.isNaN(v);
const joinPresent = (parts, sep) => parts.filter((p) => p !== null).join(sep);

function gauge(percent, detail) {
  return { hidden: false, percent, level: level(percent), value: formatPercent(percent), detail };
}

function cpu({ percent, temp_c } = {}) {
  return gauge(percent, present(temp_c) ? formatTemp(temp_c) : '');
}

function ram({ used_gb, total_gb, percent } = {}) {
  const detail = present(total_gb) ? formatUsedTotal(used_gb, total_gb) : '';
  return gauge(percent, detail);
}

function gpu(g) {
  if (!g) return { hidden: true };
  const detail = joinPresent(
    [present(g.vram_used_mb) ? formatMb(g.vram_used_mb) : null, present(g.temp_c) ? formatTemp(g.temp_c) : null],
    ' · ',
  );
  return { ...gauge(g.percent, detail), name: g.name };
}

function disk({ mount, used_gb, total_gb }) {
  const percent = total_gb > 0 ? round1((used_gb / total_gb) * 100) : 0;
  return { mount, percent, level: level(percent), detail: formatUsedTotal(used_gb, total_gb) };
}

function net({ down_kbps, up_kbps } = {}) {
  return { down_kbps, up_kbps, down: formatRate(down_kbps), up: formatRate(up_kbps) };
}

export function viewModel(stats = {}) {
  return {
    cpu: cpu(stats.cpu),
    ram: ram(stats.ram),
    gpu: gpu(stats.gpu),
    disks: (stats.disks ?? []).map(disk),
    net: net(stats.net),
  };
}

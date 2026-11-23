// Widget « Sessions IA » : badge, tri et modèle d'affichage de /api/ai.
const TOOLS = { 'claude-code': 'Claude', codex: 'Codex' };
const STATES = { working: 'en cours', idle: 'inactive', stale: 'ancienne' };
const BADGES = new Set(['working', 'idle', 'stale']);

export function sessionBadge(state) {
  return `badge-${BADGES.has(state) ? state : 'unknown'}`;
}

// working d'abord, puis la plus récemment mise à jour. Ne modifie pas `sessions`.
export function sortSessions(sessions) {
  const rank = (x) => (x.state === 'working' ? 0 : 1);
  return [...sessions].sort((a, b) => rank(a) - rank(b) || (b.updated_at ?? 0) - (a.updated_at ?? 0));
}

export function sessionsModel(ai, { maxItems = 6 } = {}) {
  const sessions = Array.isArray(ai?.sessions) ? ai.sessions : [];
  const sorted = sortSessions(sessions);
  const shown = sorted.slice(0, maxItems);
  return {
    empty: sessions.length === 0,
    items: shown.map((x) => ({
      project: x.project,
      tool: TOOLS[x.tool] ?? x.tool,
      state: STATES[x.state] ?? x.state,
      badge: sessionBadge(x.state),
    })),
    more: sorted.length - shown.length,
  };
}

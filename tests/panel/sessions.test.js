import { test } from 'node:test';
import assert from 'node:assert/strict';

import { sessionBadge, sessionsModel, sortSessions } from '../../panel/lib/sessions.js';

const s = (project, state, updated_at, tool = 'claude-code') => ({ tool, project, state, updated_at });

test('sessionBadge : classe couleur par état', () => {
  assert.equal(sessionBadge('working'), 'badge-working');
  assert.equal(sessionBadge('idle'), 'badge-idle');
  assert.equal(sessionBadge('stale'), 'badge-stale');
  assert.equal(sessionBadge('autre'), 'badge-unknown');
  assert.equal(sessionBadge(undefined), 'badge-unknown');
});

test('tri : working d’abord, puis updated_at décroissant', () => {
  const sorted = sortSessions([s('a', 'idle', 300), s('b', 'working', 100), s('c', 'idle', 500), s('d', 'working', 200)]);

  assert.deepEqual(
    sorted.map((x) => x.project),
    ['d', 'b', 'c', 'a'],
  );
});

test('tri : ne modifie pas la liste reçue', () => {
  const list = [s('a', 'idle', 1), s('b', 'working', 2)];

  sortSessions(list);

  assert.deepEqual(
    list.map((x) => x.project),
    ['a', 'b'],
  );
});

test('modèle : libellés outil et état, badge', () => {
  const vm = sessionsModel({ sessions: [s('mon-projet', 'working', 10), s('?', 'idle', 5, 'codex')] });

  assert.equal(vm.empty, false);
  assert.equal(vm.more, 0);
  assert.deepEqual(vm.items, [
    { project: 'mon-projet', tool: 'Claude', state: 'en cours', badge: 'badge-working' },
    { project: '?', tool: 'Codex', state: 'inactive', badge: 'badge-idle' },
  ]);
});

test('modèle : outil inconnu affiché tel quel', () => {
  assert.equal(sessionsModel({ sessions: [s('p', 'idle', 1, 'aider')] }).items[0].tool, 'aider');
});

test('modèle : liste vide ou réponse invalide → empty', () => {
  assert.deepEqual(sessionsModel({ sessions: [] }), { empty: true, items: [], more: 0 });
  assert.deepEqual(sessionsModel({}), { empty: true, items: [], more: 0 });
  assert.deepEqual(sessionsModel(null), { empty: true, items: [], more: 0 });
});

test('modèle : au-delà de maxItems, les plus prioritaires restent et le reste est compté', () => {
  const sessions = [s('a', 'idle', 1), s('b', 'working', 2), s('c', 'idle', 3), s('d', 'idle', 4)];

  const vm = sessionsModel({ sessions }, { maxItems: 2 });

  assert.deepEqual(
    vm.items.map((x) => x.project),
    ['b', 'd'],
  );
  assert.equal(vm.more, 2);
});

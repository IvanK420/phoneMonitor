import { test } from 'node:test';
import assert from 'node:assert/strict';

import { Poller } from '../../panel/lib/poller.js';

// Minuteries manuelles : rien ne s'exécute tant que le test ne le décide pas.
function fakeTimers() {
  let nextId = 1;
  const pending = new Map();
  return {
    pending,
    setTimeout(fn, ms) {
      const id = nextId++;
      pending.set(id, { fn, ms });
      return id;
    },
    clearTimeout(id) {
      pending.delete(id);
    },
    // Déclenche la minuterie de durée `ms` (la plus ancienne).
    fire(ms) {
      const entry = [...pending].find(([, t]) => t.ms === ms);
      assert.ok(entry, `aucune minuterie de ${ms} ms en attente`);
      pending.delete(entry[0]);
      entry[1].fn();
    },
  };
}

const ok = (body) => async () => ({ ok: true, status: 200, json: async () => body });
const http = (status) => async () => ({ ok: false, status, json: async () => ({}) });
const down = async () => {
  throw new TypeError('Failed to fetch');
};

function setup(responses) {
  const timers = fakeTimers();
  const data = [];
  const status = [];
  const calls = [];
  const poller = new Poller({
    url: '/api/stats',
    fetch: (url, init) => {
      calls.push({ url, init });
      return responses.shift()(init);
    },
    onData: (d) => data.push(d),
    onStatus: (offline) => status.push(offline),
    timers,
  });
  return { poller, timers, data, status, calls };
}

test('succès → onData reçoit le JSON', async () => {
  const { poller, data, calls } = setup([ok({ ts: 1 })]);

  await poller.tick();

  assert.deepEqual(data, [{ ts: 1 }]);
  assert.equal(poller.offline, false);
  assert.equal(calls[0].url, '/api/stats');
  assert.equal(calls[0].init.cache, 'no-store');
});

test('3 échecs consécutifs → hors ligne, signalé une seule fois', async () => {
  const { poller, status } = setup([down, down, down, down]);

  await poller.tick();
  await poller.tick();
  assert.equal(poller.offline, false);

  await poller.tick();
  assert.equal(poller.offline, true);

  await poller.tick();
  assert.deepEqual(status, [true]);
});

test('un succès remet le compteur à zéro', async () => {
  const { poller } = setup([down, down, ok({}), down, down]);

  for (let i = 0; i < 5; i++) await poller.tick();

  assert.equal(poller.offline, false);
});

test('retour en ligne après un succès', async () => {
  const { poller, status, data } = setup([down, down, down, ok({ ts: 2 })]);

  for (let i = 0; i < 4; i++) await poller.tick();

  assert.equal(poller.offline, false);
  assert.deepEqual(status, [true, false]);
  assert.deepEqual(data, [{ ts: 2 }]);
});

test('réponse HTTP en erreur ou JSON invalide → échec', async () => {
  const badJson = async () => ({
    ok: true,
    status: 200,
    json: async () => {
      throw new SyntaxError('Unexpected token');
    },
  });
  const { poller, data } = setup([http(500), http(401), badJson]);

  for (let i = 0; i < 3; i++) await poller.tick();

  assert.equal(poller.offline, true);
  assert.deepEqual(data, []);
});

test('requête bloquée → annulée après timeoutMs et comptée comme échec', async () => {
  const hanging = (init) =>
    new Promise((_, reject) => init.signal.addEventListener('abort', () => reject(new Error('aborted'))));
  const { poller, timers } = setup([hanging, hanging, hanging]);

  for (let i = 0; i < 3; i++) {
    const pending = poller.tick();
    timers.fire(1500);
    await pending;
  }

  assert.equal(poller.offline, true);
});

test('start : interroge tout de suite, puis 2 s après la fin de la requête', async () => {
  const { poller, timers, calls } = setup([ok({}), ok({}), ok({})]);

  poller.start();
  await poller.idle();
  assert.equal(calls.length, 1);

  timers.fire(2000);
  await poller.idle();
  assert.equal(calls.length, 2);
});

test('stop : plus aucune requête ni minuterie en attente', async () => {
  const { poller, timers, calls } = setup([ok({}), ok({})]);

  poller.start();
  await poller.idle();
  poller.stop();

  assert.equal(timers.pending.size, 0);
  assert.equal(calls.length, 1);
});

test('stop pendant une requête : pas de nouvelle planification', async () => {
  const { poller, timers } = setup([ok({})]);

  poller.start();
  poller.stop();
  await poller.idle();

  assert.equal(timers.pending.size, 0);
});

test('une erreur de rendu dans onData ne casse pas la boucle', async () => {
  const timers = fakeTimers();
  const errors = [];
  const poller = new Poller({
    url: '/api/stats',
    fetch: ok({}),
    onData: () => {
      throw new Error('bug de rendu');
    },
    onError: (e) => errors.push(e.message),
    timers,
  });

  poller.start();
  await poller.idle();

  assert.deepEqual(errors, ['bug de rendu']);
  assert.equal(poller.offline, false);
  assert.equal(timers.pending.size, 1); // prochaine interrogation planifiée
});

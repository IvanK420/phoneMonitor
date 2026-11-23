import { test } from 'node:test';
import assert from 'node:assert/strict';

import { formatTokens } from '../../panel/lib/format.js';
import { hourlyBarsPath, usageModel } from '../../panel/lib/usage.js';

test('formatTokens : unités k, M, G et virgule décimale', () => {
  assert.equal(formatTokens(0), '0');
  assert.equal(formatTokens(714), '714');
  assert.equal(formatTokens(1200), '1,2 k');
  assert.equal(formatTokens(33_700), '33,7 k');
  assert.equal(formatTokens(337_299), '337 k');
  assert.equal(formatTokens(63_809_128), '63,8 M');
  assert.equal(formatTokens(250_000_000), '250 M');
  assert.equal(formatTokens(1_500_000_000), '1,5 G');
  assert.equal(formatTokens(null), '—');
});

test('formatTokens : pas de « 1000 k » au passage d’unité', () => {
  assert.equal(formatTokens(999_960), '1,0 M');
  assert.equal(formatTokens(999), '999');
});

const USAGE = {
  today: { input: 714, output: 337_299, cache_read: 62_741_275, cache_creation: 729_840, total: 63_809_128 },
  window_5h: { input: 670, output: 323_472, cache_read: 61_310_208, cache_creation: 681_018, total: 62_315_368 },
  hourly: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1_395_935, 97_825, 365_885, 0, 0, 0, 36_383_043, 0, 0, 0, 0, 0, 0],
};

test('usageModel : libellés du jour, de la fenêtre 5 h, sortie et part de cache lu', () => {
  const vm = usageModel(USAGE);

  assert.equal(vm.today, '63,8 M');
  assert.equal(vm.window, '62,3 M');
  assert.equal(vm.output, '337 k');
  assert.equal(vm.cacheShare, '98 %');
  assert.deepEqual(vm.hourly, USAGE.hourly);
  assert.equal(vm.empty, false);
});

test('usageModel : journée sans activité', () => {
  const zero = { input: 0, output: 0, cache_read: 0, cache_creation: 0, total: 0 };
  const vm = usageModel({ today: zero, window_5h: zero, hourly: new Array(24).fill(0) });

  assert.equal(vm.today, '0');
  assert.equal(vm.cacheShare, '—');
  assert.equal(vm.empty, true);
});

test('usageModel : réponse absente ou incomplète → tirets, 24 heures à zéro', () => {
  for (const input of [null, undefined, {}, { today: 'x', hourly: [1, 2] }]) {
    const vm = usageModel(input);
    assert.equal(vm.today, '—');
    assert.equal(vm.window, '—');
    assert.equal(vm.hourly.length, 24);
    assert.equal(vm.empty, true);
  }
});

test('hourlyBarsPath : une barre par heure non nulle, la plus haute touche le haut', () => {
  const hourly = new Array(24).fill(0);
  hourly[0] = 50;
  hourly[23] = 100;

  // largeur 240 → 10 px par heure, barres de 8 px (1 px de marge de chaque côté)
  assert.equal(hourlyBarsPath(hourly, 240, 20), 'M1,20V10H9V20Z M231,20V0H239V20Z');
});

test('hourlyBarsPath : rien à dessiner → chaîne vide', () => {
  assert.equal(hourlyBarsPath(new Array(24).fill(0), 240, 20), '');
  assert.equal(hourlyBarsPath([], 240, 20), '');
});

test('hourlyBarsPath : une petite heure reste visible (1 px minimum)', () => {
  const hourly = new Array(24).fill(0);
  hourly[0] = 1;
  hourly[1] = 1_000_000;

  assert.match(hourlyBarsPath(hourly, 240, 20), /^M1,20V19H9V20Z/);
});

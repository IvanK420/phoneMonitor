import { test } from 'node:test';
import assert from 'node:assert/strict';

import { OLED_DEFAULTS, isNight, mergeOledConfig, pickSwap, screenMode, shiftStep, toHHMM } from '../../panel/lib/oled.js';

// --- 4.7 Décalage de pixels -----------------------------------------------------

test('shiftStep : orbite de 9 positions qui part de l’origine et boucle', () => {
  const orbit = Array.from({ length: 9 }, (_, i) => shiftStep(i));

  assert.deepEqual(orbit[0], [0, 0]);
  assert.equal(new Set(orbit.map(String)).size, 9);
  assert.deepEqual(shiftStep(9), orbit[0]);
  assert.deepEqual(shiftStep(9 * 1000 + 4), orbit[4]);
});

test('shiftStep : amplitude ≤ 3 px et pas de saut de plus d’un cran entre deux positions', () => {
  for (let i = 0; i < 9; i++) {
    const [dx, dy] = shiftStep(i);
    const [nx, ny] = shiftStep(i + 1);
    assert.ok(Math.abs(dx) <= 3 && Math.abs(dy) <= 3, `position ${i}`);
    assert.ok(Math.abs(nx - dx) <= 4 && Math.abs(ny - dy) <= 4, `transition ${i}`);
  }
});

test('shiftStep : index négatif ou non entier toléré', () => {
  assert.deepEqual(shiftStep(-1), shiftStep(8));
  assert.deepEqual(shiftStep(2.7), shiftStep(2));
});

// --- 4.8 Plage nocturne -----------------------------------------------------------

test('isNight : plage qui traverse minuit', () => {
  assert.equal(isNight('23:30', '23:00', '07:00'), true);
  assert.equal(isNight('03:00', '23:00', '07:00'), true);
  assert.equal(isNight('12:00', '23:00', '07:00'), false);
});

test('isNight : début inclus, fin exclue', () => {
  assert.equal(isNight('23:00', '23:00', '07:00'), true);
  assert.equal(isNight('07:00', '23:00', '07:00'), false);
  assert.equal(isNight('06:59', '23:00', '07:00'), true);
});

test('isNight : plage simple dans la journée', () => {
  assert.equal(isNight('13:30', '13:00', '14:00'), true);
  assert.equal(isNight('14:00', '13:00', '14:00'), false);
  assert.equal(isNight('12:59', '13:00', '14:00'), false);
});

test('isNight : plage vide ou horaire invalide → jamais', () => {
  assert.equal(isNight('12:00', '08:00', '08:00'), false);
  assert.equal(isNight('12:00', '25:00', '07:00'), false);
  assert.equal(isNight('12:00', null, '07:00'), false);
  assert.equal(isNight('midi', '23:00', '07:00'), false);
});

test('toHHMM : heure locale sur deux chiffres', () => {
  assert.equal(toHHMM(new Date(2026, 10, 23, 7, 5)), '07:05');
});

// --- 4.9 Mode d'écran ------------------------------------------------------------

const MIN = 60_000;

test('screenMode : normal, dim la nuit', () => {
  assert.equal(screenMode({ night: false, offlineSince: null, now: 0 }), 'normal');
  assert.equal(screenMode({ night: true, offlineSince: null, now: 0 }), 'dim');
});

test('screenMode : agent injoignable depuis plus de 5 min → black (prioritaire)', () => {
  assert.equal(screenMode({ night: false, offlineSince: 0, now: 5 * MIN }), 'normal');
  assert.equal(screenMode({ night: false, offlineSince: 0, now: 5 * MIN + 1 }), 'black');
  assert.equal(screenMode({ night: true, offlineSince: 0, now: 10 * MIN }), 'black');
});

// --- 4.10 Permutation de tuiles ---------------------------------------------------

const TILES = [
  { id: 'cpu', size: 'gauge' },
  { id: 'ram', size: 'gauge' },
  { id: 'gpu', size: 'gauge' },
  { id: 'net', size: 'wide' },
  { id: 'ai', size: 'narrow' },
];
const seq = (...values) => {
  let i = 0;
  return () => values[i++ % values.length];
};

test('pickSwap : deux tuiles distinctes de même taille', () => {
  const pair = pickSwap(TILES, seq(0, 0.99), { swapMinutes: 20 });

  assert.equal(pair.length, 2);
  assert.notEqual(pair[0], pair[1]);
  const sizes = pair.map((id) => TILES.find((t) => t.id === id).size);
  assert.equal(sizes[0], sizes[1]);
});

test('pickSwap : quel que soit le tirage, jamais de taille différente', () => {
  for (let a = 0; a < 1; a += 0.1) {
    for (let b = 0; b < 1; b += 0.1) {
      const pair = pickSwap(TILES, seq(a, b), { swapMinutes: 20 });
      assert.deepEqual(new Set(pair.map((id) => TILES.find((t) => t.id === id).size)).size, 1);
    }
  }
});

test('pickSwap : désactivé (0), alerte active ou interaction → jamais', () => {
  assert.equal(pickSwap(TILES, Math.random, { swapMinutes: 0 }), null);
  assert.equal(pickSwap(TILES, Math.random, { swapMinutes: 20, alertActive: true }), null);
  assert.equal(pickSwap(TILES, Math.random, { swapMinutes: 20, interacting: true }), null);
});

test('pickSwap : aucune paire possible → null', () => {
  const tiles = [
    { id: 'a', size: 'x' },
    { id: 'b', size: 'y' },
  ];
  assert.equal(pickSwap(tiles, Math.random, { swapMinutes: 20 }), null);
});

// --- 4.11 Fusion de la configuration -----------------------------------------------

test('défauts du doc 03', () => {
  assert.deepEqual(OLED_DEFAULTS, {
    pixel_shift: true,
    shift_interval_s: 90,
    night_start: '23:00',
    night_end: '07:00',
    night_brightness: 0.1,
    swap_minutes: 0,
  });
  assert.deepEqual(mergeOledConfig(undefined), OLED_DEFAULTS);
});

test('surcharge partielle', () => {
  assert.deepEqual(mergeOledConfig({ swap_minutes: 20, night_start: '22:30' }), {
    ...OLED_DEFAULTS,
    swap_minutes: 20,
    night_start: '22:30',
  });
});

test('valeurs de mauvais type ou clés inconnues ignorées', () => {
  assert.deepEqual(mergeOledConfig({ pixel_shift: 'oui', shift_interval_s: '90', inconnu: 1, night_end: '7h' }), OLED_DEFAULTS);
});

test('valeurs numériques bornées', () => {
  const merged = mergeOledConfig({ night_brightness: 3, shift_interval_s: 1, swap_minutes: -5 });

  assert.equal(merged.night_brightness, 1);
  assert.equal(merged.shift_interval_s, 5);
  assert.equal(merged.swap_minutes, 0);
});

test('ne modifie pas les défauts partagés', () => {
  mergeOledConfig({ swap_minutes: 30 });

  assert.equal(OLED_DEFAULTS.swap_minutes, 0);
});

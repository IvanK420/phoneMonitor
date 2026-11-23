import { test } from 'node:test';
import assert from 'node:assert/strict';

import { level } from '../../panel/lib/thresholds.js';

test('sous 70 % : ok', () => {
  assert.equal(level(0), 'ok');
  assert.equal(level(69.9), 'ok');
});

test('de 70 à 90 % inclus : warn', () => {
  assert.equal(level(70), 'warn');
  assert.equal(level(90), 'warn');
});

test('au-delà de 90 % : crit', () => {
  assert.equal(level(90.1), 'crit');
  assert.equal(level(100), 'crit');
});

test('valeur absente : unknown', () => {
  assert.equal(level(null), 'unknown');
  assert.equal(level(undefined), 'unknown');
  assert.equal(level(Number.NaN), 'unknown');
});

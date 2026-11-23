import { test } from 'node:test';
import assert from 'node:assert/strict';

import { formatGb, formatPercent, formatRate, formatTemp, formatMb } from '../../panel/lib/format.js';

test('formatGb : virgule décimale, un chiffre sous 100 Go, entier au-delà', () => {
  assert.equal(formatGb(11.24), '11,2 Go');
  assert.equal(formatGb(32), '32,0 Go');
  assert.equal(formatGb(410.04), '410 Go');
  assert.equal(formatGb(0), '0,0 Go');
});

test('formatGb : au-delà de 1000 Go, en To', () => {
  assert.equal(formatGb(1863), '1,8 To');
});

test('formatRate : kb/s, Mb/s, Gb/s', () => {
  assert.equal(formatRate(0), '0 kb/s');
  assert.equal(formatRate(85), '85 kb/s');
  assert.equal(formatRate(999), '999 kb/s');
  assert.equal(formatRate(1200), '1,2 Mb/s');
  assert.equal(formatRate(250_000), '250 Mb/s');
  assert.equal(formatRate(1_500_000), '1,5 Gb/s');
});

test('formatPercent : entier arrondi', () => {
  assert.equal(formatPercent(23.5), '24 %');
  assert.equal(formatPercent(0), '0 %');
});

test('formatTemp et formatMb', () => {
  assert.equal(formatTemp(57.8), '58 °C');
  assert.equal(formatMb(2100), '2 100 Mo');
});

test('valeur absente : tiret cadratin', () => {
  for (const fn of [formatGb, formatRate, formatPercent, formatTemp, formatMb]) {
    assert.equal(fn(null), '—', fn.name);
    assert.equal(fn(undefined), '—', fn.name);
  }
});

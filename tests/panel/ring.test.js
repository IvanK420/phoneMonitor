import { test } from 'node:test';
import assert from 'node:assert/strict';

import { Ring } from '../../panel/lib/ring.js';

test('capacité 60 par défaut', () => {
  assert.equal(new Ring().capacity, 60);
});

test("l'ajout du 61ᵉ point éjecte le 1ᵉʳ", () => {
  const ring = new Ring();
  for (let i = 1; i <= 61; i++) ring.push(i);

  const values = ring.values();
  assert.equal(values.length, 60);
  assert.equal(values[0], 2);
  assert.equal(values.at(-1), 61);
});

test('la mémoire reste bornée après un très grand nombre d’ajouts', () => {
  const ring = new Ring(3);
  for (let i = 0; i < 10_000; i++) ring.push(i);

  assert.deepEqual(ring.values(), [9997, 9998, 9999]);
});

test('max() des valeurs présentes, 0 si vide', () => {
  const ring = new Ring(5);
  assert.equal(ring.max(), 0);
  ring.push(3);
  ring.push(7);
  ring.push(1);
  assert.equal(ring.max(), 7);
});

test('valeur absente ou négative enregistrée comme 0', () => {
  const ring = new Ring(3);
  ring.push(null);
  ring.push(-5);
  assert.deepEqual(ring.values(), [0, 0]);
});

test('toPath : vide → chaîne vide', () => {
  assert.equal(new Ring(4).toPath(100, 10), '');
});

test('toPath : points alignés à droite, max en haut, 0 en bas', () => {
  const ring = new Ring(5); // pas horizontal = 100 / 4 = 25
  ring.push(0);
  ring.push(5);
  ring.push(10);

  assert.equal(ring.toPath(100, 10), 'M50,10 L75,5 L100,0');
});

test('toPath : échelle imposée (pour partager l’axe entre deux séries)', () => {
  const ring = new Ring(2);
  ring.push(5);
  ring.push(5);

  assert.equal(ring.toPath(10, 10, 20), 'M0,7.5 L10,7.5'); // 5/20 de la hauteur
});

test('toPath : série toute à zéro → ligne de base, pas de division par zéro', () => {
  const ring = new Ring(2);
  ring.push(0);
  ring.push(0);

  assert.equal(ring.toPath(10, 10), 'M0,10 L10,10');
});

test('toPath : coordonnées arrondies au dixième', () => {
  const ring = new Ring(4); // pas = 10 / 3
  ring.push(1);
  ring.push(2);
  ring.push(3);
  ring.push(3);

  assert.equal(ring.toPath(10, 10), 'M0,6.7 L3.3,3.3 L6.7,0 L10,0');
});

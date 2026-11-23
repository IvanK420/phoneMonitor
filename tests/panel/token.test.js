import { test } from 'node:test';
import assert from 'node:assert/strict';

import { resolveToken, storedToken, TOKEN_KEY } from '../../panel/lib/token.js';

function memoryStorage(initial = {}) {
  const data = { ...initial };
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => {
      data[k] = String(v);
    },
  };
}

test('jeton dans l’URL : mémorisé, puis retiré de l’adresse', () => {
  const storage = memoryStorage();

  const result = resolveToken('http://192.168.1.20:8765/?token=ABC', storage);

  assert.equal(result.token, 'ABC');
  assert.equal(result.cleanUrl, 'http://192.168.1.20:8765/');
  assert.equal(storage.data[TOKEN_KEY], 'ABC');
});

test('les autres paramètres et le fragment sont conservés', () => {
  const result = resolveToken('http://h:8765/?v=2&token=ABC#x', memoryStorage());

  assert.equal(result.cleanUrl, 'http://h:8765/?v=2#x');
});

test('sans jeton dans l’URL : celui mémorisé, adresse inchangée', () => {
  const result = resolveToken('http://h:8765/', memoryStorage({ [TOKEN_KEY]: 'SAVED' }));

  assert.deepEqual(result, { token: 'SAVED', cleanUrl: null });
});

test('un nouveau jeton dans l’URL remplace l’ancien', () => {
  const storage = memoryStorage({ [TOKEN_KEY]: 'OLD' });

  assert.equal(resolveToken('http://h/?token=NEW', storage).token, 'NEW');
  assert.equal(storage.data[TOKEN_KEY], 'NEW');
});

test('aucun jeton nulle part : null', () => {
  assert.deepEqual(resolveToken('http://h/', memoryStorage()), { token: null, cleanUrl: null });
});

test('stockage indisponible (navigation privée) : le jeton de l’URL sert quand même', () => {
  const broken = {
    getItem() {
      throw new Error('SecurityError');
    },
    setItem() {
      throw new Error('QuotaExceededError');
    },
  };

  assert.equal(resolveToken('http://h/?token=ABC', broken).token, 'ABC');
  assert.deepEqual(resolveToken('http://h/', broken), { token: null, cleanUrl: null });
});

test('storedToken : relit le jeton mémorisé, null si absent ou stockage indisponible', () => {
  assert.equal(storedToken(memoryStorage({ [TOKEN_KEY]: 'X' })), 'X');
  assert.equal(storedToken(memoryStorage()), null);
  assert.equal(
    storedToken({
      getItem() {
        throw new Error('SecurityError');
      },
    }),
    null,
  );
});

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { VERSION } from '../../panel/lib/version.js';

test('les modules du panneau sont importables depuis Node', () => {
  assert.match(VERSION, /^\d+\.\d+\.\d+$/);
});

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { viewModel } from '../../panel/lib/app-model.js';

const STATS = {
  ts: 1731672000,
  cpu: { percent: 23.5, temp_c: 58 },
  ram: { used_gb: 11.2, total_gb: 32, percent: 35 },
  gpu: { name: 'RTX 4070', percent: 92, vram_used_mb: 2100, temp_c: 49 },
  disks: [{ mount: 'C:', used_gb: 410, total_gb: 953 }],
  net: { down_kbps: 1200, up_kbps: 85 },
};

test('CPU : jauge, niveau, libellé, température', () => {
  assert.deepEqual(viewModel(STATS).cpu, {
    hidden: false,
    percent: 23.5,
    level: 'ok',
    value: '24 %',
    detail: '58 °C',
  });
});

test('CPU sans température : détail vide', () => {
  const vm = viewModel({ ...STATS, cpu: { percent: 75, temp_c: null } });

  assert.equal(vm.cpu.detail, '');
  assert.equal(vm.cpu.level, 'warn');
});

test('RAM : utilisé / total', () => {
  assert.deepEqual(viewModel(STATS).ram, {
    hidden: false,
    percent: 35,
    level: 'ok',
    value: '35 %',
    detail: '11,2 Go / 32,0 Go',
  });
});

test('GPU présent : nom, VRAM et température', () => {
  assert.deepEqual(viewModel(STATS).gpu, {
    hidden: false,
    percent: 92,
    level: 'crit',
    value: '92 %',
    detail: '2 100 Mo · 49 °C',
    name: 'RTX 4070',
  });
});

test('gpu: null → widget GPU masqué', () => {
  assert.deepEqual(viewModel({ ...STATS, gpu: null }).gpu, { hidden: true });
});

test('GPU aux valeurs [N/A] : libellés tirets, niveau unknown', () => {
  const vm = viewModel({ ...STATS, gpu: { name: 'GTX 1050', percent: null, vram_used_mb: 512, temp_c: null } });

  assert.equal(vm.gpu.value, '—');
  assert.equal(vm.gpu.level, 'unknown');
  assert.equal(vm.gpu.detail, '512 Mo');
});

test('disques : pourcentage calculé et niveau', () => {
  assert.deepEqual(viewModel(STATS).disks, [
    { mount: 'C:', percent: 43, level: 'ok', detail: '410 Go / 953 Go' },
  ]);
});

test('disque presque plein → crit ; total nul → 0 %', () => {
  const vm = viewModel({
    ...STATS,
    disks: [
      { mount: 'D:', used_gb: 95, total_gb: 100 },
      { mount: 'E:', used_gb: 0, total_gb: 0 },
    ],
  });

  assert.deepEqual(
    vm.disks.map((d) => [d.mount, d.percent, d.level]),
    [
      ['D:', 95, 'crit'],
      ['E:', 0, 'ok'],
    ],
  );
});

test('réseau : valeurs brutes pour la sparkline et libellés', () => {
  assert.deepEqual(viewModel(STATS).net, {
    down_kbps: 1200,
    up_kbps: 85,
    down: '1,2 Mb/s',
    up: '85 kb/s',
  });
});

test('réponse incomplète : aucune exception, valeurs par défaut', () => {
  const vm = viewModel({});

  assert.equal(vm.cpu.value, '—');
  assert.equal(vm.ram.value, '—');
  assert.equal(vm.gpu.hidden, true);
  assert.deepEqual(vm.disks, []);
  assert.equal(vm.net.down, '—');
});

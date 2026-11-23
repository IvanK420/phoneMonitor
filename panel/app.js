// Colle DOM uniquement : toutes les décisions sont dans lib/ (testées avec node --test).
import { viewModel } from './lib/app-model.js';
import { Poller } from './lib/poller.js';
import { Ring } from './lib/ring.js';
import { VERSION } from './lib/version.js';

const SPARK_W = 300;
const SPARK_H = 100;

const $ = (selector, root = document) => root.querySelector(selector);
const clampPercent = (p) => Math.min(100, Math.max(0, typeof p === 'number' ? p : 0));

const downRing = new Ring(60);
const upRing = new Ring(60);

function renderGauge(id, gauge) {
  const tile = document.getElementById(id);
  tile.hidden = gauge.hidden;
  if (gauge.hidden) return;
  tile.dataset.level = gauge.level;
  $('.arc', tile).setAttribute('stroke-dasharray', `${clampPercent(gauge.percent)} 100`);
  $('.value', tile).textContent = gauge.value;
  $('.detail', tile).textContent = gauge.detail;
  const name = $('.name', tile);
  if (name) name.textContent = gauge.name ?? '';
}

function renderNet(net) {
  const tile = document.getElementById('net');
  downRing.push(net.down_kbps);
  upRing.push(net.up_kbps);
  const scale = Math.max(downRing.max(), upRing.max());
  $('.down b', tile).textContent = net.down;
  $('.up b', tile).textContent = net.up;
  $('.down-line', tile).setAttribute('d', downRing.toPath(SPARK_W, SPARK_H, scale));
  $('.up-line', tile).setAttribute('d', upRing.toPath(SPARK_W, SPARK_H, scale));
}

function diskRow(disk) {
  const row = document.createElement('div');
  row.className = 'disk';
  const mount = document.createElement('span');
  mount.className = 'mount';
  const bar = document.createElement('div');
  bar.className = 'bar';
  bar.append(document.createElement('span'));
  const detail = document.createElement('span');
  detail.className = 'detail';
  row.append(mount, bar, detail);
  return row;
}

function renderDisks(disks) {
  const container = document.getElementById('disks');
  // On ne recrée les lignes que si le nombre de volumes change (clé USB branchée…).
  if (container.children.length !== disks.length) container.replaceChildren(...disks.map(diskRow));
  disks.forEach((disk, i) => {
    const row = container.children[i];
    row.dataset.level = disk.level;
    $('.mount', row).textContent = disk.mount;
    $('.bar > span', row).style.setProperty('--p', `${clampPercent(disk.percent)}%`);
    $('.detail', row).textContent = disk.detail;
  });
}

function render(stats) {
  const vm = viewModel(stats);
  renderGauge('cpu', vm.cpu);
  renderGauge('ram', vm.ram);
  renderGauge('gpu', vm.gpu);
  renderNet(vm.net);
  renderDisks(vm.disks);
}

function setOffline(offline) {
  document.body.classList.toggle('offline', offline);
  document.getElementById('status').hidden = !offline;
}

// Version en info-bulle plutôt qu'à l'écran : rien de fixe qui marque l'OLED.
document.getElementById('root').title = `PhoneBox Lite v${VERSION}`;

new Poller({ url: '/api/stats', onData: render, onStatus: setOffline }).start();

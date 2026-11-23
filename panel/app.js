// Colle DOM uniquement : toutes les décisions sont dans lib/ (testées avec node --test).
import { viewModel } from './lib/app-model.js';
import { Poller } from './lib/poller.js';
import { Ring } from './lib/ring.js';
import { mergeOledConfig } from './lib/oled.js';
import { sessionsModel } from './lib/sessions.js';
import { resolveToken } from './lib/token.js';
import { VERSION } from './lib/version.js';
import { Screen } from './screen.js';

const SPARK_W = 300;
const SPARK_H = 100;
const AI_MAX_ITEMS = 4; // ce qui tient dans la tuile en paysage téléphone

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

function sessionRow({ project, tool, state, badge }) {
  const row = document.createElement('li');
  row.className = 'session';
  const dot = document.createElement('span');
  dot.className = `dot ${badge}`;
  dot.title = state;
  const name = document.createElement('span');
  name.className = 'project';
  name.textContent = project;
  const meta = document.createElement('span');
  meta.className = 'meta';
  meta.textContent = `${tool} · ${state}`;
  row.append(dot, name, meta);
  return row;
}

// Clé de rendu : on ne touche au DOM que si la liste affichée change (l'animation du point reste fluide).
let lastSessionsKey = '';

function renderSessions(ai) {
  const vm = sessionsModel(ai, { maxItems: AI_MAX_ITEMS });
  const key = JSON.stringify(vm);
  if (key === lastSessionsKey) return;
  lastSessionsKey = key;
  document.getElementById('ai-list').replaceChildren(...vm.items.map(sessionRow));
  document.getElementById('ai-empty').hidden = !vm.empty;
  const more = document.getElementById('ai-more');
  more.hidden = vm.more === 0;
  more.textContent = `+${vm.more} autre${vm.more > 1 ? 's' : ''}`;
}

function render(stats) {
  const vm = viewModel(stats);
  renderGauge('cpu', vm.cpu);
  renderGauge('ram', vm.ram);
  renderGauge('gpu', vm.gpu);
  renderNet(vm.net);
  renderDisks(vm.disks);
}

// Pastille d'état : « hors ligne » (réseau) ou « jeton invalide » (agent joignable, accès refusé).
const problems = { offline: false, auth: false };

function updateStatus() {
  const status = document.getElementById('status');
  document.body.classList.toggle('offline', problems.offline || problems.auth);
  status.hidden = !problems.offline && !problems.auth;
  status.textContent = problems.auth ? 'Jeton invalide — ouvrir l’URL affichée par l’agent' : 'Hors ligne';
}

// Le simple accès à `localStorage` peut lever (cookies bloqués) : stockage vide en repli.
function safeLocalStorage() {
  try {
    return window.localStorage;
  } catch {
    return { getItem: () => null, setItem: () => {} };
  }
}

async function loadOledConfig(headers) {
  try {
    const response = await fetch('/api/config', { headers, cache: 'no-store' });
    if (response.ok) return mergeOledConfig((await response.json()).oled);
  } catch {
    // agent injoignable au démarrage : réglages par défaut
  }
  return mergeOledConfig(undefined);
}

async function main() {
  // Version en info-bulle plutôt qu'à l'écran : rien de fixe qui marque l'OLED.
  document.getElementById('root').title = `PhoneBox Lite v${VERSION}`;

  const { token, cleanUrl } = resolveToken(location.href, safeLocalStorage());
  if (cleanUrl) history.replaceState(null, '', cleanUrl);
  const headers = token ? { 'X-Token': token } : {};

  const screenControl = new Screen(document.getElementById('root'), await loadOledConfig(headers));
  screenControl.start();

  new Poller({
    url: '/api/stats',
    headers,
    onData: render,
    onStatus: (offline) => {
      problems.offline = offline;
      screenControl.setOffline(offline);
      updateStatus();
    },
    onAuthError: (bad) => {
      problems.auth = bad;
      updateStatus();
    },
  }).start();
  // Seul le sondage des stats pilote l'indicateur d'état.
  new Poller({ url: '/api/ai', headers, onData: renderSessions }).start();
}

main();

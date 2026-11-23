// Colle navigateur pour l'écran du téléphone : protection OLED, Wake Lock, plein écran.
// Les décisions (horaires, modes, choix des tuiles) sont dans lib/oled.js, testé avec node --test.
import { isNight, pickSwap, screenMode, shiftStep, toHHMM } from './lib/oled.js';

const MODE_CHECK_MS = 30_000;
const INTERACTION_GRACE_MS = 10_000;
const SWAP_ANIMATION_MS = 600;

export class Screen {
  #config;
  #root;
  #offlineSince = null;
  #lastTouch = 0;
  #shiftIndex = 0;
  #wakeLock = null;

  constructor(root, config) {
    this.#root = root;
    this.#config = config;
  }

  start() {
    document.documentElement.style.setProperty('--night-brightness', String(this.#config.night_brightness));
    if (this.#config.pixel_shift) setInterval(() => this.#shift(), this.#config.shift_interval_s * 1000);
    if (this.#config.swap_minutes > 0) setInterval(() => this.#swapTiles(), this.#config.swap_minutes * 60_000);
    setInterval(() => this.#applyMode(), MODE_CHECK_MS);
    this.#applyMode();

    document.addEventListener('pointerdown', () => {
      this.#lastTouch = Date.now();
    });
    this.#setupFullscreen();
    this.#setupWakeLock();
  }

  setOffline(offline) {
    this.#offlineSince = offline ? (this.#offlineSince ?? Date.now()) : null;
    this.#applyMode();
  }

  // --- Décalage de pixels : contenu ET message de veille bougent ensemble ---------------
  #shift() {
    const [dx, dy] = shiftStep(++this.#shiftIndex);
    document.documentElement.style.setProperty('--dx', `${dx}px`);
    document.documentElement.style.setProperty('--dy', `${dy}px`);
  }

  // --- Nuit (atténué) et agent injoignable > 5 min (écran noir) -------------------------
  #applyMode() {
    const { night_start, night_end } = this.#config;
    const mode = screenMode({
      night: isNight(toHHMM(new Date()), night_start, night_end),
      offlineSince: this.#offlineSince,
      now: Date.now(),
    });
    document.body.dataset.mode = mode;
  }

  // --- Permutation de deux tuiles de même taille, animation FLIP --------------------------
  #swapTiles() {
    const tiles = [...document.querySelectorAll('.gauges > .tile:not([hidden])')];
    const pair = pickSwap(
      tiles.map((el) => ({ id: el.id, size: 'gauge' })),
      Math.random,
      {
        swapMinutes: this.#config.swap_minutes,
        alertActive: document.querySelector('[data-level="crit"]') !== null,
        interacting: Date.now() - this.#lastTouch < INTERACTION_GRACE_MS,
      },
    );
    if (!pair) return;

    const [a, b] = pair.map((id) => document.getElementById(id));
    const before = new Map([a, b].map((el) => [el, el.getBoundingClientRect()]));

    const marker = document.createElement('span');
    a.replaceWith(marker);
    b.replaceWith(a);
    marker.replaceWith(b);

    for (const el of [a, b]) {
      const from = before.get(el);
      const to = el.getBoundingClientRect();
      el.animate(
        [{ transform: `translate(${from.left - to.left}px, ${from.top - to.top}px)` }, { transform: 'none' }],
        { duration: SWAP_ANIMATION_MS, easing: 'ease-in-out' },
      );
    }
  }

  // --- Plein écran : exige un geste de l'utilisateur ---------------------------------------
  #setupFullscreen() {
    const start = document.getElementById('start');
    const button = document.getElementById('fullscreen');
    const canFullscreen = typeof document.documentElement.requestFullscreen === 'function';
    const update = () => {
      button.hidden = !canFullscreen || document.fullscreenElement !== null;
      // Revenu hors plein écran (geste retour) : on repropose le bouton.
      if (!document.fullscreenElement && canFullscreen) start.hidden = false;
    };
    // Rien de fixe ne doit rester à l'écran (OLED) : l'encart disparaît au premier toucher.
    document.addEventListener('click', () => {
      start.hidden = true;
    });
    const enter = async () => {
      if (!canFullscreen || document.fullscreenElement) return;
      try {
        await document.documentElement.requestFullscreen({ navigationUI: 'hide' });
        await screen.orientation?.lock?.('landscape').catch(() => {});
      } catch {
        // refusé (navigateur, iframe…) : le panneau reste utilisable
      }
    };
    button.addEventListener('click', enter);
    document.addEventListener('fullscreenchange', update);
    update();
  }

  // --- Wake Lock : réacquis à chaque retour au premier plan (libéré par le navigateur) ----
  #setupWakeLock() {
    const status = document.getElementById('wakelock');
    if (!('wakeLock' in navigator)) {
      // Contexte non sécurisé (http://<ip-lan>) : API absente. Voir README (« Rester activé »).
      status.hidden = false;
      return;
    }
    const acquire = async () => {
      if (document.visibilityState !== 'visible' || this.#wakeLock) return;
      try {
        this.#wakeLock = await navigator.wakeLock.request('screen');
        this.#wakeLock.addEventListener('release', () => {
          this.#wakeLock = null;
        });
      } catch {
        // batterie faible, onglet masqué… : nouvel essai au prochain retour au premier plan
      }
    };
    document.addEventListener('visibilitychange', acquire);
    document.addEventListener('pointerdown', acquire);
    acquire();
  }
}

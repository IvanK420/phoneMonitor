// Sondage de l'agent : requêtes chaînées (jamais deux en vol), délai max par requête,
// passage « hors ligne » après N échecs consécutifs (03-interface.md).
const defaultTimers = {
  setTimeout: (fn, ms) => globalThis.setTimeout(fn, ms),
  clearTimeout: (id) => globalThis.clearTimeout(id),
};

export class Poller {
  #failures = 0;
  #offline = false;
  #running = false;
  #timer = null;
  #inflight = Promise.resolve();
  #authError = false;

  constructor({
    url,
    fetch = (...args) => globalThis.fetch(...args),
    onData,
    onStatus = () => {},
    onError = (err) => console.error(err),
    onAuthError = () => {},
    headers = {},
    intervalMs = 2000,
    timeoutMs = 1500,
    maxFailures = 3,
    timers = defaultTimers,
    now = () => globalThis.performance.now(),
  }) {
    Object.assign(this, { url, fetch, onData, onStatus, onError, onAuthError, headers, intervalMs, timeoutMs, maxFailures, timers, now });
  }

  get offline() {
    return this.#offline;
  }

  async tick() {
    const controller = new AbortController();
    const timeout = this.timers.setTimeout(() => controller.abort(), this.timeoutMs);
    let data;
    try {
      const response = await this.fetch(this.url, {
        cache: 'no-store',
        headers: typeof this.headers === 'function' ? this.headers() : this.headers,
        signal: controller.signal,
      });
      // Agent joignable mais jeton refusé : ce n'est pas une panne réseau, on le signale à part.
      this.#setAuthError(response.status === 401);
      if (response.status === 401) {
        this.#succeed(); // l'agent répond : pas « hors ligne »
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      data = await response.json();
    } catch {
      this.#fail();
      return;
    } finally {
      this.timers.clearTimeout(timeout);
    }
    this.#succeed();
    this.onData(data);
  }

  start() {
    if (this.#running) return;
    this.#running = true;
    this.#loop();
  }

  stop() {
    this.#running = false;
    if (this.#timer !== null) this.timers.clearTimeout(this.#timer);
    this.#timer = null;
  }

  // Résolue quand la requête en cours (s'il y en a une) est terminée — utile aux tests.
  idle() {
    return this.#inflight;
  }

  // Cadence fixe : la requête suivante part `intervalMs` après le DÉBUT de la précédente,
  // pour qu'une requête lente (agent figé) n'allonge pas le délai avant « hors ligne ».
  #loop() {
    this.#timer = null;
    const startedAt = this.now();
    this.#inflight = this.tick()
      .catch((err) => this.onError(err)) // un bug de rendu ne doit pas arrêter le sondage
      .then(() => {
        if (!this.#running) return;
        const wait = Math.max(0, this.intervalMs - (this.now() - startedAt));
        this.#timer = this.timers.setTimeout(() => this.#loop(), wait);
      });
  }

  #fail() {
    this.#failures++;
    if (!this.#offline && this.#failures >= this.maxFailures) this.#setOffline(true);
  }

  #succeed() {
    this.#failures = 0;
    if (this.#offline) this.#setOffline(false);
  }

  #setAuthError(value) {
    if (value === this.#authError) return;
    this.#authError = value;
    this.onAuthError(value);
  }

  #setOffline(value) {
    this.#offline = value;
    this.onStatus(value);
  }
}

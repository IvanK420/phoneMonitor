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

  constructor({
    url,
    fetch = (...args) => globalThis.fetch(...args),
    onData,
    onStatus = () => {},
    onError = (err) => console.error(err),
    intervalMs = 2000,
    timeoutMs = 1500,
    maxFailures = 3,
    timers = defaultTimers,
  }) {
    Object.assign(this, { url, fetch, onData, onStatus, onError, intervalMs, timeoutMs, maxFailures, timers });
  }

  get offline() {
    return this.#offline;
  }

  async tick() {
    const controller = new AbortController();
    const timeout = this.timers.setTimeout(() => controller.abort(), this.timeoutMs);
    let data;
    try {
      const response = await this.fetch(this.url, { cache: 'no-store', signal: controller.signal });
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

  #loop() {
    this.#timer = null;
    this.#inflight = this.tick()
      .catch((err) => this.onError(err)) // un bug de rendu ne doit pas arrêter le sondage
      .then(() => {
        if (this.#running) this.#timer = this.timers.setTimeout(() => this.#loop(), this.intervalMs);
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

  #setOffline(value) {
    this.#offline = value;
    this.onStatus(value);
  }
}

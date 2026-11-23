// Tampon circulaire de taille fixe pour les sparklines : la mémoire reste bornée sur 24 h.
const round1 = (n) => Math.round(n * 10) / 10;

export class Ring {
  #data;
  #start = 0;
  #size = 0;

  constructor(capacity = 60) {
    this.capacity = capacity;
    this.#data = new Array(capacity).fill(0);
  }

  push(value) {
    const v = typeof value === 'number' && value > 0 ? value : 0;
    const end = (this.#start + this.#size) % this.capacity;
    this.#data[end] = v;
    if (this.#size < this.capacity) this.#size++;
    else this.#start = (this.#start + 1) % this.capacity;
  }

  values() {
    const out = new Array(this.#size);
    for (let i = 0; i < this.#size; i++) out[i] = this.#data[(this.#start + i) % this.capacity];
    return out;
  }

  max() {
    return this.values().reduce((m, v) => Math.max(m, v), 0);
  }

  // Chemin SVG dans une boîte w × h : le point le plus récent à droite, `scale` en haut.
  toPath(w, h, scale = this.max()) {
    const values = this.values();
    if (values.length === 0) return '';
    const step = this.capacity > 1 ? w / (this.capacity - 1) : 0;
    const offset = w - (values.length - 1) * step;
    return values
      .map((v, i) => {
        const x = round1(offset + i * step);
        const y = round1(scale > 0 ? h - (Math.min(v, scale) / scale) * h : h);
        return `${i === 0 ? 'M' : 'L'}${x},${y}`;
      })
      .join(' ');
  }
}

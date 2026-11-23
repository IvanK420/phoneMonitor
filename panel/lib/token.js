// Jeton d'accès : reçu une fois dans l'URL (?token=…, affichée par l'agent), mémorisé ensuite.
// Il est retiré de la barre d'adresse pour ne pas rester visible ni dans l'historique partagé.
export const TOKEN_KEY = 'phonebox.token';

// Relu à chaque requête : un jeton reçu dans un autre onglet est pris en compte sans recharger.
export function storedToken(storage) {
  try {
    return storage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function write(storage, token) {
  try {
    storage.setItem(TOKEN_KEY, token);
  } catch {
    // navigation privée, quota… : le jeton de l'URL sert pour cette session
  }
}

export function resolveToken(href, storage) {
  const url = new URL(href);
  const fromUrl = url.searchParams.get('token');
  if (!fromUrl) return { token: storedToken(storage), cleanUrl: null };

  write(storage, fromUrl);
  url.searchParams.delete('token');
  return { token: fromUrl, cleanUrl: url.toString() };
}

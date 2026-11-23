// Jeton d'accès : reçu une fois dans l'URL (?token=…, affichée par l'agent), mémorisé ensuite.
// Il est retiré de la barre d'adresse pour ne pas rester visible ni dans l'historique partagé.
export const TOKEN_KEY = 'phonebox.token';

function read(storage) {
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
  if (!fromUrl) return { token: read(storage), cleanUrl: null };

  write(storage, fromUrl);
  url.searchParams.delete('token');
  return { token: fromUrl, cleanUrl: url.toString() };
}

const DIACRITICS_PATTERN = /[\u0300-\u036f]/g;

/** Devuelve una ruta comparable con los slugs canónicos ASCII. */
export function normalizeRoutePath(pathname: string): string {
  let decodedPathname = pathname;

  try {
    decodedPathname = decodeURI(pathname);
  } catch {
    // Una URL incompleta no debe romper la shell de navegación.
  }

  return decodedPathname.normalize('NFD').replace(DIACRITICS_PATTERN, '').toLowerCase();
}

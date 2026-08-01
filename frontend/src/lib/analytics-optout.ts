/**
 * Exclusión permanente de un navegador de toda la analítica del sitio.
 *
 * Visitar `residenciafiscal.org/?no_analytics=1` una vez deja una marca en
 * `localStorage` y a partir de ahí ni GA4 ni PostHog se instalan en ese
 * navegador. `?no_analytics=0` la retira.
 *
 * Se eligió `localStorage` y no un filtro por IP porque la IP doméstica es
 * dinámica y no cubre los datos móviles: la marca viaja con el navegador, que
 * es lo que realmente identifica «nuestras propias visitas».
 */

export const ANALYTICS_OPTOUT_PARAM = 'no_analytics';
export const ANALYTICS_OPTOUT_KEY = 'residenciafiscal:analytics-optout';

/**
 * `localStorage` lanza en Safari privado y con cookies de terceros bloqueadas.
 * Un fallo aquí nunca debe romper la página, así que se degrada a «sin marca».
 */
const readStorage = (): Storage | null => {
  try {
    return typeof window === 'undefined' ? null : window.localStorage;
  } catch {
    return null;
  }
};

/** Lee el parámetro de la URL y persiste (o retira) la marca de exclusión. */
export const syncAnalyticsOptOut = (search?: string): void => {
  if (typeof window === 'undefined') return;
  const value = new URLSearchParams(search ?? window.location.search).get(ANALYTICS_OPTOUT_PARAM);
  if (value === null) return;

  const storage = readStorage();
  if (!storage) return;
  try {
    if (value === '0' || value === 'false') {
      storage.removeItem(ANALYTICS_OPTOUT_KEY);
    } else {
      storage.setItem(ANALYTICS_OPTOUT_KEY, new Date().toISOString());
    }
  } catch {
    // Cuota llena o almacenamiento bloqueado: no hay marca que guardar.
  }
};

/** `true` si este navegador quedó excluido de la analítica. */
export const hasAnalyticsOptOut = (): boolean => {
  const storage = readStorage();
  if (!storage) return false;
  try {
    return storage.getItem(ANALYTICS_OPTOUT_KEY) !== null;
  } catch {
    return false;
  }
};

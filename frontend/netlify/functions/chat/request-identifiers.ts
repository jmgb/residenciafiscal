/**
 * Validadores compartidos por los endpoints del chat. Viven aparte de `chat.ts`
 * porque ese módulo compone las dependencias de producción al importarse.
 */

export const validIdentifier = (value: unknown): value is string =>
  typeof value === 'string' && value.length >= 1 && value.length <= 128 && /^[\w-]+$/.test(value);

export const validCountryPath = (value: unknown): value is string =>
  typeof value === 'string' && /^\/[a-z0-9-]{1,63}$/.test(value);

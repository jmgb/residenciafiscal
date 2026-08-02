import {
  counterpartNamesWithSeveralTreaties,
  jurisdictionSectionPath,
  treatyCounterpartName,
} from '@/data/jurisdictions';
import fichas from '@/data/normativaFichas.json';
import type { PreceptoEntry } from '@/types/normativa';

/**
 * Metadatos SEO de las fichas de precepto (`/espana/normativa/<slug>`).
 *
 * Mismo contrato que `countryRoutes.json` y `staticRoutes.json`: el título y la
 * descripción que escribe el prerender son exactamente los que fija la página
 * en runtime, porque salen de estas funciones y de ningún otro sitio.
 *
 * El nombre común del país de cada convenio no existe en el corpus normativo
 * —el BOE solo da el título oficial—, así que sale del registro bilateral a
 * través de `jurisdictions.ts`. Antes vivía duplicado aquí, y una ficha podía
 * decir «Méjico» mientras la página del país decía «México».
 */

const NORMAS: Record<string, string> = fichas.normas;

/**
 * Países con más de un convenio (Argentina, Reino Unido, Japón, Rumanía y
 * China). Su ficha lleva el año en el título, porque «Artículo 4 del CDI
 * España-Japón» nombraría igual a dos preceptos distintos.
 */
const PAISES_REPETIDOS = counterpartNamesWithSeveralTreaties();

export const NORMATIVA_INDEX_PATH = jurisdictionSectionPath('es', 'normativa');

export function fichaPathForSlug(slug: string): string {
  return `${NORMATIVA_INDEX_PATH}/${slug}`;
}

export function fichaPath(entry: PreceptoEntry): string {
  return fichaPathForSlug(entry.slug);
}

/** Nombre común de la contraparte del convenio; `null` si no es un CDI. */
export function paisDelConvenio(entry: PreceptoEntry): string | null {
  if (!entry.grupo.startsWith('cdi')) return null;
  return treatyCounterpartName(entry.boeId);
}

function nombreODenominacion(entry: PreceptoEntry): string {
  // El test de cobertura hace imposible llegar aquí sin país; el fallback
  // existe para que un dato inesperado no publique «España-undefined».
  return paisDelConvenio(entry) ?? entry.boeId;
}

function normaCorta(entry: PreceptoEntry): string {
  return NORMAS[entry.boeId] ?? `de ${entry.boeId}`;
}

/** Año de la redacción vigente, para distinguir convenios sucesivos. */
function anioVigencia(entry: PreceptoEntry): string {
  return entry.vigenteDesde?.slice(0, 4) ?? entry.boeId.split('-')[2];
}

export function fichaTitle(entry: PreceptoEntry): string {
  if (entry.grupo.startsWith('cdi')) {
    const pais = nombreODenominacion(entry);
    if (entry.derogada) {
      return `${entry.designacion} del CDI España-${pais}, derogado`;
    }
    const anio = PAISES_REPETIDOS.has(pais) ? ` (${anioVigencia(entry)})` : '';
    return `${entry.designacion} del CDI España-${pais}${anio}: residencia fiscal`;
  }
  if (entry.derogada) {
    return `${entry.designacion} ${normaCorta(entry)}, derogado — texto del BOE`;
  }
  return `${entry.designacion} ${normaCorta(entry)} — texto del BOE`;
}

export function fichaDescription(entry: PreceptoEntry): string {
  const articulo = entry.designacion.toLowerCase();
  if (entry.grupo.startsWith('cdi')) {
    const pais = nombreODenominacion(entry);
    if (entry.derogada) {
      return (
        `Convenio ya derogado que rigió ejercicios anteriores: texto literal del ${articulo} de ` +
        `residencia del CDI España-${pais}, conservado porque sentencias del corpus lo aplican.`
      );
    }
    return (
      `Texto literal del ${articulo} del convenio de doble imposición entre España y ${pais}: ` +
      'la regla que decide la residencia fiscal entre los dos países. Fuente: BOE.'
    );
  }
  if (entry.derogada) {
    return (
      `Norma derogada que rige ejercicios anteriores del corpus: texto literal del ${articulo} ` +
      `${normaCorta(entry)}, tal y como lo publicó el BOE.`
    );
  }
  // El epígrafe oficial lleva las palabras que se buscan («residencia
  // habitual», «certificado de residencia fiscal»…); el título no siempre cabe
  // con él, la descripción sí.
  const epigrafe = entry.epigrafe ? `: ${entry.epigrafe}` : '';
  return `Texto literal del ${articulo} ${normaCorta(entry)}${epigrafe}. Fuente: BOE, redacción vigente.`;
}

/** Encabezado visible de la ficha; el epígrafe oficial va aparte. */
export function fichaHeading(entry: PreceptoEntry): string {
  if (entry.grupo.startsWith('cdi')) {
    const pais = nombreODenominacion(entry);
    const anio = PAISES_REPETIDOS.has(pais) ? ` (${anioVigencia(entry)})` : '';
    return `${entry.designacion} del convenio España-${pais}${anio}`;
  }
  return `${entry.designacion} ${normaCorta(entry)}`;
}

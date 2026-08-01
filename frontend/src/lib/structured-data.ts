/**
 * Datos estructurados `schema.org` de las páginas de país, en JSON-LD.
 *
 * Solo se declaran dos tipos, y los dos describen algo que la página tiene de
 * verdad: `BreadcrumbList` para la jerarquía del sitio y `Legislation` para el
 * artículo de residencia del convenio, que es norma española publicada en el
 * BOE. No hay `FAQPage` —no hay preguntas— ni `Article` —no hay autor humano—:
 * marcar contenido que no existe es exactamente lo que penaliza un buscador.
 *
 * Todos los campos salen del corpus normativo versionado. Lo que el corpus no
 * sabe se omite en lugar de rellenarse por inferencia, igual que en el resto
 * del proyecto.
 */
import type { CountryRoute } from '@/data/countryRoutes';
import type { PreceptoEntry } from '@/types/normativa';

const SITE_URL = 'https://residenciafiscal.org';
const SITE_NAME = 'Residencia Fiscal';

interface ListItem {
  '@type': 'ListItem';
  position: number;
  name: string;
  item: string;
}

export interface BreadcrumbList {
  '@context': 'https://schema.org';
  '@type': 'BreadcrumbList';
  itemListElement: ListItem[];
}

export interface Legislation {
  '@context': 'https://schema.org';
  '@type': 'Legislation';
  name: string;
  legislationIdentifier: string;
  inLanguage: 'es';
  /** El convenio es norma española; no describe el derecho interno del otro país. */
  legislationJurisdiction: 'España';
  legislationLegalForce: string;
  isPartOf: { '@type': 'Legislation'; name: string };
  url?: string;
  legislationDateVersion?: string;
}

/** Jerarquía de la ruta: la home del sitio y la página del país. */
export function breadcrumbJsonLd(country: CountryRoute): BreadcrumbList {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: SITE_NAME, item: `${SITE_URL}/` },
      {
        '@type': 'ListItem',
        position: 2,
        name: country.name,
        item: `${SITE_URL}${country.path}`,
      },
    ],
  };
}

/**
 * Artículo de residencia del convenio con España.
 *
 * `isPartOf` separa el precepto de la norma que lo contiene, que es como lo
 * guarda el corpus: `titulo` es el artículo y `norma` el convenio entero.
 */
export function treatyJsonLd(entry: PreceptoEntry): Legislation {
  const legislation: Legislation = {
    '@context': 'https://schema.org',
    '@type': 'Legislation',
    name: entry.titulo,
    legislationIdentifier: entry.boeId,
    inLanguage: 'es',
    legislationJurisdiction: 'España',
    // `derogada` lo decide el corpus normativo, no una fecha calculada aquí.
    legislationLegalForce: entry.derogada
      ? 'https://schema.org/NotInForce'
      : 'https://schema.org/InForce',
    isPartOf: { '@type': 'Legislation', name: entry.norma },
  };

  if (entry.urlBoe) legislation.url = entry.urlBoe;
  // `vigenteDesde` es la redacción consolidada que se publica, no la fecha de
  // adopción del convenio: `legislationDate` afirmaría un dato que no tenemos.
  if (entry.vigenteDesde) legislation.legislationDateVersion = entry.vigenteDesde;

  return legislation;
}

/**
 * Serializa el JSON-LD para incrustarlo en un `<script>`.
 *
 * `<` va escapado porque el texto viene del BOE: un `</script>` dentro de un
 * título cerraría la etiqueta y rompería el documento. Mismo criterio que la
 * precarga del convenio en `scripts/prerender.mjs`.
 */
export function jsonLdScript(value: unknown): string {
  return JSON.stringify(value).replace(/</g, '\\u003c');
}

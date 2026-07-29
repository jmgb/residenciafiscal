/**
 * Tipos del corpus normativo. Los produce `scripts/build-normativa.mjs` a partir
 * de `knowledge/normativa/<jurisdiccion>/`, que a su vez sale del XML del BOE.
 *
 * El articulado es **texto legal literal**: se muestra o no se muestra, pero no
 * se reescribe, recorta ni parafrasea en ningún punto del frontend.
 */

export type GrupoPrecepto = 'nucleo' | 'nucleo_derogado' | 'cdi' | 'cdi_derogado';

/** Certeza con la que se resolvió una cita de una sentencia a este precepto. */
export type CertezaCita = 'explicita' | 'inferida';

export interface CitaSentencia {
  archivo: string;
  roj: string | null;
  ejercicios: number[];
  certeza: CertezaCita;
}

/** Entrada del índice: metadatos, sin articulado. */
export interface PreceptoEntry {
  slug: string;
  jurisdiccion: string;
  titulo: string;
  norma: string;
  designacion: string;
  epigrafe: string | null;
  grupo: GrupoPrecepto;
  boeId: string;
  urlBoe: string | null;
  /** Una norma derogada no es derecho aplicable hoy; la UI debe decirlo. */
  derogada: boolean;
  notaDerogacion: string | null;
  vigenteDesde: string | null;
  /** Número de redacciones sucesivas que conserva el precepto. */
  redacciones: number;
  parrafos: number;
  sentencias: CitaSentencia[];
  totalSentencias: number;
}

/** Articulado literal de un precepto, servido en su propio fichero. */
export interface PreceptoTexto extends Omit<PreceptoEntry, 'parrafos' | 'totalSentencias'> {
  articulado: string[];
  redaccionesAnteriores: string[];
  notasBoe: string[];
}

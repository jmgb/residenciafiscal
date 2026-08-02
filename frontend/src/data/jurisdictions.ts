import { z } from 'zod';
import jurisdictionData from './jurisdictions.json';
import treatyRelationData from './treatyRelations.json';

/**
 * Catálogo de jurisdicciones y relaciones bilaterales, proyectados desde el
 * dato de dominio (`src/jurisdiction_catalog.json` y `src/treaty_relations_es.json`).
 *
 * Los dos JSON los **genera** `src/export_frontend_projections.py` y se
 * versionan para que un clon limpio de Netlify no dependa de ejecutar Python.
 * Editarlos a mano no sirve: la siguiente ejecución los sobrescribe, y
 * `tests/test_frontend_projections.py` falla si quedan desincronizados.
 *
 * `code` (ISO 3166-1 alfa-2, o alfa-4 del 3166-3 para Checoslovaquia y la URSS)
 * es la única clave de cruce. El `slug` decide la URL y puede cambiar con una
 * migración; por eso las rutas se construyen desde aquí y no concatenando
 * nombres por ahí sueltos.
 */

const jurisdictionSchema = z.object({
  name: z.string().min(1),
  slug: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
});

const instrumentSchema = z.object({
  boeId: z.string().startsWith('BOE-A-'),
  status: z.enum(['current', 'superseded']),
  /** Primer y último ejercicio fiscal en los que se aplica; `null` = sin límite. */
  fromTaxYear: z.number().int().nullable(),
  toTaxYear: z.number().int().nullable(),
});

export type Jurisdiction = z.infer<typeof jurisdictionSchema>;
export type TreatyInstrument = z.infer<typeof instrumentSchema>;

const JURISDICTIONS = z
  .record(z.string(), jurisdictionSchema)
  .parse(jurisdictionData.jurisdictions);

const BY_COUNTERPART = z
  .record(z.string(), z.array(instrumentSchema).min(1))
  .parse(treatyRelationData.byCounterpart);

const BY_BOE_ID = z.record(z.string(), z.string()).parse(treatyRelationData.byBoeId);

/** Nombre en español de la jurisdicción. Lanza si el código no está: un país
 * desconocido debe romper el build, no publicarse como «undefined». */
export function jurisdictionName(code: string): string {
  const jurisdiction = JURISDICTIONS[code];
  if (!jurisdiction) {
    throw new Error(`La jurisdicción «${code}» no está en el catálogo compartido.`);
  }
  return jurisdiction.name;
}

/** Ruta pública de la jurisdicción. Única construcción de URL de país. */
export function jurisdictionPath(code: string): string {
  const jurisdiction = JURISDICTIONS[code];
  if (!jurisdiction) {
    throw new Error(`La jurisdicción «${code}» no está en el catálogo compartido.`);
  }
  return `/${jurisdiction.slug}`;
}

/** Convenios firmados con esa contraparte, del más antiguo al vigente. */
export function treatyInstruments(code: string): TreatyInstrument[] {
  return BY_COUNTERPART[code] ?? [];
}

/**
 * Convenio de doble imposición en vigor entre España y esa jurisdicción, o
 * `null` si no hay ninguno. `null` significa que no existe convenio según la
 * relación oficial, no que no se haya buscado.
 */
export function currentTreatyBoeId(code: string): string | null {
  return (
    treatyInstruments(code).find((instrument) => instrument.status === 'current')?.boeId ?? null
  );
}

/** Jurisdicción con la que España firmó ese convenio, o `null`.
 *
 * El país **no** se deduce del título de la norma: los convenios lo escriben de
 * trece formas distintas y un país equivocado publicaría el derecho de otro
 * Estado con el nombre correcto encima. */
export function treatyCounterpart(boeId: string): string | null {
  return BY_BOE_ID[boeId] ?? null;
}

/** Nombre común de la contraparte de un convenio, o `null` si no lo es. */
export function treatyCounterpartName(boeId: string): string | null {
  const code = treatyCounterpart(boeId);
  return code ? jurisdictionName(code) : null;
}

/**
 * Países con más de un convenio en el corpus: Argentina, Reino Unido, Japón,
 * Rumanía y China. Su ficha necesita el año en el título, porque «Artículo 4
 * del CDI España-Japón» nombraría igual a dos preceptos distintos.
 */
export function counterpartNamesWithSeveralTreaties(): Set<string> {
  return new Set(
    Object.entries(BY_COUNTERPART)
      .filter(([, instruments]) => instruments.length > 1)
      .map(([code]) => jurisdictionName(code))
  );
}

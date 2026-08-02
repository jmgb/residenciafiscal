import { describe, expect, it } from 'vitest';
import {
  criterioLabel,
  esBorrador,
  fechaLarga,
  MAX_DESCRIPTION,
  resultadoLabel,
  revisionLabel,
  sentenciaDescription,
  sentenciaPath,
  sentenciaTitle,
} from '@/lib/sentencia-metadata';
import type { SentenciaIndexEntry } from '@/types/sentencias';

/**
 * §5.5 del diseño: los metadatos de cada ficha salen del dato, no de copy por
 * página. Con 67 fichas, un texto escrito a mano acabaría produciendo títulos y
 * descripciones repetidos, que es lo que hace que Google elija por su cuenta qué
 * indexar.
 */
const BASE: SentenciaIndexEntry = {
  judgmentId: 'san-1386-2017',
  roj: 'SAN 1386/2017',
  court: 'Audiencia Nacional, Sala de lo Contencioso-Administrativo',
  decisionDate: '2017-03-30',
  taxYears: [2009],
  criterionIds: ['CRIT_183_DIAS', 'CRIT_CDI_TIEBREAKER'],
  outcomes: ['GANA_CONTRIBUYENTE'],
  jurisdictions: ['ch', 'es'],
  publicationState: 'internal_preview',
  legalReview: 'AGENT_REVIEWED',
};

describe('metadatos de la ficha de sentencia', () => {
  it('el título lleva la entidad primero y el órgano legible', () => {
    expect(sentenciaTitle(BASE)).toBe(
      'SAN 1386/2017 (Audiencia Nacional): residencia fiscal, ejercicio 2009'
    );
  });

  it('resume varios ejercicios como un rango', () => {
    expect(sentenciaTitle({ ...BASE, taxYears: [2010, 2011, 2012] })).toContain(
      'ejercicios 2010-2012'
    );
  });

  it('la fecha se publica en castellano, no en ISO', () => {
    expect(fechaLarga('2017-03-30')).toBe('30 de marzo de 2017');
    // Una fecha que no reconoce se devuelve tal cual antes que inventar un mes.
    expect(fechaLarga('no-es-una-fecha')).toBe('no-es-una-fecha');
  });

  it('la descripción cabe en lo que muestra el buscador', () => {
    const largo: SentenciaIndexEntry = {
      ...BASE,
      criterionIds: [
        'CRIT_183_DIAS',
        'CRIT_AUSENCIAS_ESPORADICAS',
        'CRIT_CENTRO_INTERESES_ECONOMICOS',
        'CRIT_CENTRO_INTERESES_VITALES',
        'CRIT_PRESUNCION_FAMILIA',
      ],
      outcomes: ['GANA_AEAT', 'GANA_CONTRIBUYENTE', 'RETROACCION'],
      decisionDate: '2020-09-30',
    };

    const descripcion = sentenciaDescription(largo);

    expect(descripcion.length).toBeLessThanOrEqual(MAX_DESCRIPTION);
    // Lo que nunca se cae al recortar es el ROJ ni el resultado.
    expect(descripcion).toContain('SAN 1386/2017');
    expect(descripcion).toContain('Resultado:');
  });

  it('la ruta es el identificador del corpus, estable y legible', () => {
    expect(sentenciaPath('san-1386-2017')).toBe('/espana/sentencias/san-1386-2017');
  });

  it('traduce criterios y resultados del catálogo canónico', () => {
    expect(criterioLabel('CRIT_AUSENCIAS_ESPORADICAS')).toBe('Ausencias esporádicas');
    expect(resultadoLabel('RETROACCION')).toBe('Retroacción de actuaciones');
    // Un valor que el catálogo no tenga se muestra tal cual: inventar una
    // etiqueta ocultaría que el corpus trae algo inesperado.
    expect(criterioLabel('CRIT_NUEVO')).toBe('CRIT_NUEVO');
  });

  it('nunca presenta un análisis del agente como revisado por una persona', () => {
    expect(revisionLabel('AGENT_REVIEWED')).toMatch(/pendiente de revisión humana/);
    expect(revisionLabel('AGENT_REVIEWED')).not.toMatch(/expert/i);
    expect(revisionLabel('HUMAN_APPROVED')).toMatch(/aprobado por revisión humana/);
  });

  it('solo `published` deja de ser borrador', () => {
    expect(esBorrador({ publicationState: 'internal_preview' })).toBe(true);
    expect(esBorrador({ publicationState: 'publishable' })).toBe(true);
    expect(esBorrador({ publicationState: 'published' })).toBe(false);
  });
});

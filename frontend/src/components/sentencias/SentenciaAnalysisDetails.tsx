import type { AnalisisConvenio, PeriodoPresencia } from '@/types/sentencias';

const EVIDENCE_CATEGORY: Record<string, string> = {
  PRESENCIA_FISICA_Y_DESPLAZAMIENTOS: 'Presencia física y desplazamientos',
  VIVIENDA_Y_USO_EFECTIVO: 'Vivienda y uso efectivo',
  SUMINISTROS_Y_CONSUMOS_DOMESTICOS: 'Suministros y consumos domésticos',
  CONSUMOS_FINANCIEROS: 'Consumos financieros',
  FAMILIA_Y_ENTORNO_PERSONAL: 'Familia y entorno personal',
  SALUD_Y_SERVICIOS_PERSONALES: 'Salud y servicios personales',
  ACTIVIDAD_ECONOMICA_Y_GESTION: 'Actividad económica y gestión',
  DOCUMENTACION_FISCAL_EXTRANJERA: 'Documentación fiscal extranjera',
  VINCULOS_ADMINISTRATIVOS_EN_ESPANA: 'Vínculos administrativos en España',
  TRAZAS_DIGITALES: 'Trazas digitales',
  TESTIFICAL_Y_PERICIAL: 'Prueba testifical y pericial',
  OTROS: 'Otras pruebas',
};

const PRESENCE_CLASSIFICATION: Record<string, string> = {
  PRESENT: 'Presencia',
  ABSENT: 'Ausencia',
  SPORADIC_ABSENCE: 'Ausencia esporádica',
  UNKNOWN: 'Situación no determinada',
};

const TREATY_CRITERION: Record<string, string> = {
  VIVIENDA_PERMANENTE: 'Vivienda permanente',
  CENTRO_INTERESES_VITALES: 'Centro de intereses vitales',
  MORADA_HABITUAL: 'Morada habitual',
  NACIONALIDAD: 'Nacionalidad',
  ACUERDO_MUTUO: 'Procedimiento amistoso',
  NO_CONSTA: 'No consta',
  NO_APLICA: 'No se aplica',
};

export function evidenceCategoryLabel(category: string): string {
  return EVIDENCE_CATEGORY[category] ?? category;
}

export function presenceSummary(period: PeriodoPresencia): string {
  const classification = PRESENCE_CLASSIFICATION[period.classification] ?? period.classification;
  if (period.countedFor183DayRule === true) {
    return `${classification} · computa para la regla de 183 días`;
  }
  if (period.countedFor183DayRule === false) {
    return `${classification} · no computa para la regla de 183 días`;
  }
  return classification;
}

export function TreatyAnalysisList({ analyses }: { analyses: AnalisisConvenio[] }) {
  return (
    <ul className='space-y-2 text-sm leading-relaxed'>
      {analyses.map((analysis) => (
        <li key={analysis.treatyAnalysisId}>
          {analysis.treatyCitation}
          {analysis.resultCountry && (
            <span className='text-muted-foreground'>
              {' '}
              · residencia atribuida a {analysis.resultCountry}
            </span>
          )}
          {analysis.steps.length > 0 && (
            <ol className='mt-1 space-y-1 pl-4'>
              {analysis.steps.map((step) => (
                <li key={step.stepId}>
                  <span className='font-medium'>
                    {TREATY_CRITERION[step.criterion] ?? step.criterion}:
                  </span>{' '}
                  {step.conclusion}
                </li>
              ))}
            </ol>
          )}
        </li>
      ))}
    </ul>
  );
}

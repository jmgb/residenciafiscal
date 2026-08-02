import { criterioLabel, resultadoLabel } from '@/lib/sentencia-metadata';
import type { CuestionJuridica } from '@/types/sentencias';
import {
  evidenceCategoryLabel,
  presenceSummary,
  TreatyAnalysisList,
} from './SentenciaAnalysisDetails';

/**
 * Una cuestión jurídica de la sentencia con lo que el tribunal decidió sobre
 * ella: hechos, pruebas valoradas, normas, carga de la prueba, cronología y
 * convenio, y la conclusión.
 *
 * Las secciones vacías **no se pintan**. 62 de los 67 casos no tienen hechos
 * tipados, y un epígrafe «Hechos relevantes» seguido de nada sugeriría que la
 * sentencia no los tiene, que es distinto de que el corpus no los haya
 * modelado todavía.
 *
 * Nada de aquí es texto judicial: es análisis estructurado y la página lo
 * rotula como tal. Lo literal vive en los anclajes.
 */

const OFRECIDA_POR: Record<string, string> = {
  AEAT: 'Aportada por la Administración',
  TAXPAYER: 'Aportada por el contribuyente',
  COURT: 'Incorporada por el tribunal',
};

const VALORACION: Record<string, string> = {
  ACCEPTED: 'Aceptada',
  REJECTED: 'Rechazada',
  PARTIAL: 'Aceptada en parte',
  NOT_ASSESSED: 'Sin valorar',
};

const SUJETO_CARGA: Record<string, string> = {
  AEAT: 'la Administración',
  TAXPAYER: 'el contribuyente',
};

function Bloque({
  titulo,
  children,
  vacio = false,
}: {
  titulo: string;
  children: React.ReactNode;
  vacio?: boolean;
}) {
  if (vacio) return null;
  return (
    <section className='mt-4'>
      <h3 className='mb-1.5 font-heading font-semibold text-sm'>{titulo}</h3>
      {children}
    </section>
  );
}

export function CuestionSection({ cuestion }: { cuestion: CuestionJuridica }) {
  const { holding } = cuestion;

  return (
    <article className='border-border border-t pt-6'>
      <h2 className='mb-2 font-heading font-semibold text-lg'>{cuestion.question}</h2>

      <div className='flex flex-wrap gap-1.5'>
        {holding && (
          <span className='rounded bg-muted px-1.5 py-0.5 text-secondary-foreground text-xs'>
            {resultadoLabel(holding.outcome)}
          </span>
        )}
        {cuestion.criterionIds.map((criterio) => (
          <span
            key={criterio}
            className='rounded bg-muted px-1.5 py-0.5 text-secondary-foreground text-xs'
          >
            {criterioLabel(criterio)}
          </span>
        ))}
      </div>

      <Bloque titulo='Hechos relevantes' vacio={cuestion.facts.length === 0}>
        <ul className='space-y-1.5 text-sm leading-relaxed'>
          {cuestion.facts.map((hecho) => (
            <li key={hecho.factId}>
              {hecho.description}
              {hecho.place && <span className='text-muted-foreground'> ({hecho.place})</span>}
            </li>
          ))}
        </ul>
      </Bloque>

      <Bloque titulo='Pruebas valoradas' vacio={cuestion.evidence.length === 0}>
        <ul className='space-y-2 text-sm leading-relaxed'>
          {cuestion.evidence.map((prueba) => (
            <li key={prueba.evidenceId}>
              <span className='font-medium'>{prueba.description}</span>
              <span className='block text-muted-foreground text-xs'>
                {evidenceCategoryLabel(prueba.category)} ·{' '}
                {OFRECIDA_POR[prueba.offeredBy] ?? prueba.offeredBy} ·{' '}
                {VALORACION[prueba.assessment] ?? prueba.assessment}
                {prueba.assessmentReason && `: ${prueba.assessmentReason}`}
              </span>
            </li>
          ))}
        </ul>
      </Bloque>

      <Bloque titulo='Normas y doctrina aplicadas' vacio={cuestion.legalRules.length === 0}>
        <ul className='space-y-1.5 text-sm leading-relaxed'>
          {cuestion.legalRules.map((norma) => (
            <li key={norma.legalRuleId}>
              <span className='font-medium'>{norma.citation}</span>: {norma.proposition}
            </li>
          ))}
        </ul>
      </Bloque>

      <Bloque titulo='Carga de la prueba' vacio={cuestion.burdenOfProof.length === 0}>
        <ol className='space-y-1.5 text-sm leading-relaxed'>
          {cuestion.burdenOfProof.map((paso) => (
            <li key={paso.stepId}>
              Corresponde a {SUJETO_CARGA[paso.initialBearer] ?? paso.initialBearer} acreditar:{' '}
              {paso.factToProve}
              {paso.shiftsTo && (
                <span className='text-muted-foreground'>
                  {' '}
                  · se traslada a {SUJETO_CARGA[paso.shiftsTo] ?? paso.shiftsTo}
                </span>
              )}
              {paso.responseRequired && (
                <span className='block text-muted-foreground text-xs'>
                  Respuesta exigida: {paso.responseRequired}
                </span>
              )}
              {paso.conclusion && <span className='block text-xs'>{paso.conclusion}</span>}
            </li>
          ))}
        </ol>
      </Bloque>

      <Bloque titulo='Cronología de presencia' vacio={cuestion.presencePeriods.length === 0}>
        <ul className='space-y-1.5 text-sm leading-relaxed'>
          {cuestion.presencePeriods.map((periodo) => (
            <li key={periodo.periodId}>
              {periodo.country ?? 'Sin país declarado'}
              {periodo.startDate && `, desde ${periodo.startDate}`}
              {periodo.endDate && ` hasta ${periodo.endDate}`}
              {typeof periodo.dayCount === 'number' && ` · ${periodo.dayCount} días`}
              <span className='block text-muted-foreground text-xs'>
                {presenceSummary(periodo)}
              </span>
              {periodo.calculationMethod && (
                <span className='block text-muted-foreground text-xs'>
                  {periodo.calculationMethod}
                </span>
              )}
            </li>
          ))}
        </ul>
      </Bloque>

      <Bloque titulo='Convenio de doble imposición' vacio={cuestion.treatyAnalyses.length === 0}>
        <TreatyAnalysisList analyses={cuestion.treatyAnalyses} />
      </Bloque>

      {holding && (
        <Bloque titulo='Conclusión'>
          <p className='text-sm leading-relaxed'>{holding.conclusion}</p>
          {holding.decisiveReasoning && (
            <p className='mt-1.5 text-muted-foreground text-sm leading-relaxed'>
              {holding.decisiveReasoning}
            </p>
          )}
          {holding.consequences.length > 0 && (
            <ul className='mt-1.5 space-y-1 text-sm leading-relaxed'>
              {holding.consequences.map((consecuencia) => (
                <li key={consecuencia}>{consecuencia}</li>
              ))}
            </ul>
          )}
        </Bloque>
      )}
    </article>
  );
}

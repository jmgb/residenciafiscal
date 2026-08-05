import { claimHasLexicalEvidence } from './claim-evidence-relevance';
import type { StrategyAnswer } from './contracts';
import { buildEvidenceBundle } from './evidence-bundle';
import {
  authorityLabel,
  authorityMatch,
  localAuthorityFilter,
  requestedJudicialAuthority,
} from './judicial-authority';
import { marginalCost, zeroCost } from './pricing';
import type { NetlifyChatStrategy, StrategyContext } from './runtime';
import { retrieveForChat } from './structured-retrieval';

const MODEL = 'gpt-5.6-luna';
const REASONING_EFFORT = 'high';
export const STRUCTURED_PROMPT_VERSION = 'structured-claims-v5';

const systemPrompt =
  'Actúa como asistente de investigación jurisprudencial sobre residencia fiscal de personas físicas en IRPF y CDI, no sobre extranjería. Responde solo con el contexto recuperado. La primera claim debe contestar directamente a lo preguntado, siempre que exista respaldo literal. Si la pregunta contiene varias partes, contesta cada una mediante claims separadas o identifica expresamente en limits la parte que la evidencia no permite resolver. Si una parte carece de respaldo, no crees una claim para esa parte ni afirmes que no existe jurisprudencia: identifícala solo en limits. Devuelve afirmaciones jurídicas atómicas: separa hechos acreditados, valoración judicial y resultado, y no mezcles permanencia física, ausencias esporádicas, certificados fiscales extranjeros ni reglas de desempate de CDI en una misma afirmación. Cada claim debe declarar kind: party_argument para alegaciones o actuaciones de una parte, judicial_assessment para valoración del tribunal, legal_rule para reglas jurídicas, holding para el resultado o criterio decisorio y procedural_power para facultades o carga probatoria. Cuando la pregunta pida cómo puede Hacienda demostrar un hecho, distingue obligatoriamente los medios utilizados o alegados, su valoración judicial y el resultado probatorio. No presentes como medio eficaz una actuación que la resolución citada rechazó o consideró insuficiente; si solo existe cita de la alegación, di que Hacienda la alegó o intentó y no afirmes su suficiencia. En indicios de vida cotidiana, aclara en la misma claim que una mera alta, titularidad o pago de cuota no equivale por sí solo a presencia física en una fecha; distingue esos datos del uso efectivo atribuible al contribuyente y de su valoración conjunta con otros indicios. No relegues una insuficiencia probatoria decisiva al campo limits: intégrala en la respuesta principal con su cita. Para preguntas sobre prueba de permanencia, ordena la respuesta en pruebas directas, indicios corroborativos, elementos insuficientes por sí solos y carga de la prueba, incluyendo solo los bloques respaldados. Muestra contraste cuando exista. No predigas el caso del usuario ni uses conocimiento externo. Si la pregunta pide un tribunal concreto, atribuye doctrina o criterios a ese tribunal solo cuando el judgment_id de la evidencia corresponda directamente a ese órgano; una sentencia que cita a otra es autoridad indirecta y debe declararse como límite. Recibirás fragmentos literales con IDs E<n>: cada claim debe incluir todos y solo los IDs cuyos extractos literales permiten comprobar íntegramente la afirmación. Nunca uses un evidence_id que no aparezca en el contexto. Los campos estructurados sirven para localizar el asunto, pero no bastan para respaldar una claim: si el extracto solo menciona una prueba, no infieras de ahí que el tribunal la aceptó, rechazó o consideró decisiva. No añadas introducciones o conclusiones sustantivas fuera de claims. Incluye siempre limits y claims.';

export type StructuredClaimKind =
  | 'party_argument'
  | 'judicial_assessment'
  | 'legal_rule'
  | 'holding'
  | 'procedural_power';

export interface StructuredClaim {
  kind: StructuredClaimKind;
  text: string;
  evidence_ids: string[];
}

export interface StructuredDraft {
  status: 'completa' | 'parcial' | 'pregunta' | 'abstención';
  claims: StructuredClaim[];
  limits: string[];
}

export interface StructuredWriterResult {
  draft: StructuredDraft;
  usage: { input_tokens: number; output_tokens: number; complete: boolean };
  model: string;
}

export interface StructuredWriter {
  write(input: {
    systemPrompt: string;
    userPrompt: string;
    model: string;
    reasoningEffort: 'high';
    requestId: string;
    signal: AbortSignal;
  }): Promise<StructuredWriterResult>;
}

const nonAnswerText = (
  status: StrategyAnswer['status'],
  reasons: string[],
  missingFacts: string[],
  uncoveredFacets: string[]
) => {
  if (status === 'pregunta' && missingFacts.length) {
    return `Para buscar casos realmente comparables necesito que indiques: ${missingFacts.join('; ')}.`;
  }
  if (status === 'abstención') {
    return `El corpus actual no cubre con suficiente precisión esta cuestión: ${uncoveredFacets.join('; ') || reasons.join(' ')}.`;
  }
  return reasons.join(' ');
};

export class CurrentStructuredStrategy implements NetlifyChatStrategy {
  readonly id = 'current_structured' as const;

  constructor(
    private readonly corpus: unknown,
    private readonly writer: StructuredWriter,
    private readonly verbatimArtifacts?: Parameters<typeof buildEvidenceBundle>[3]
  ) {}

  async answer(question: string, context: StrategyContext): Promise<StrategyAnswer> {
    const started = performance.now();
    const authorityIntent = requestedJudicialAuthority(question);
    const retrieval = retrieveForChat(this.corpus, question, 5);
    const status = {
      responder: 'completa',
      parcial: 'parcial',
      preguntar: 'pregunta',
      abstenerse: 'abstención',
    }[retrieval.behavior] as StrategyAnswer['status'];
    const retrievalLimits = [
      ...(status === 'pregunta' ? retrieval.missingFacts : []),
      ...retrieval.uncoveredFacets,
    ];
    if (status === 'pregunta' || status === 'abstención') {
      return {
        strategy: this.id,
        status,
        text: nonAnswerText(
          status,
          retrieval.behaviorReasons,
          retrieval.missingFacts,
          retrieval.uncoveredFacets
        ),
        sources: [],
        limits: retrievalLimits,
        cost: zeroCost(MODEL),
        model: 'deterministic-structured-v3',
        reasoning_effort: null,
        latency_ms: Math.round(performance.now() - started),
      };
    }

    const bundle = buildEvidenceBundle(this.corpus, retrieval, question, this.verbatimArtifacts);
    const written = await this.writer.write({
      systemPrompt,
      userPrompt: `Pregunta del usuario:\n${question}\n\nContexto estructurado recuperado:\n${bundle.contextJson}`,
      model: MODEL,
      reasoningEffort: REASONING_EFFORT,
      requestId: context.requestId,
      signal: context.signal,
    });
    const cost = marginalCost(MODEL, {
      inputTokens: written.usage.input_tokens,
      outputTokens: written.usage.output_tokens,
      retrievedDocumentTokens: 0,
      complete: written.usage.complete,
    });
    const claimsWithoutEvidence = written.draft.claims.filter(
      (claim) => !claim.text.trim() || claim.evidence_ids.length === 0
    );
    const candidateEvidenceIds = [
      ...new Set(written.draft.claims.flatMap((claim) => claim.evidence_ids)),
    ];
    const unknown = candidateEvidenceIds.filter((id) => !bundle.sourcesByEvidenceId.has(id));
    const claimsWithIncompatiblePurpose = unknown.length
      ? []
      : written.draft.claims.filter((claim) => {
          const purposes = claim.evidence_ids.map((id) => bundle.purposesByEvidenceId.get(id));
          if (claim.kind === 'holding') return !purposes.includes('HOLDING');
          if (claim.kind === 'judicial_assessment') {
            return !purposes.some((purpose) =>
              ['REASONING', 'HOLDING', 'BURDEN_OF_PROOF'].includes(String(purpose))
            );
          }
          if (claim.kind === 'legal_rule') {
            return !purposes.some((purpose) =>
              ['LEGAL_RULE', 'REASONING', 'HOLDING'].includes(String(purpose))
            );
          }
          if (claim.kind === 'procedural_power') {
            return !purposes.some((purpose) =>
              ['BURDEN_OF_PROOF', 'LEGAL_RULE', 'REASONING', 'HOLDING'].includes(String(purpose))
            );
          }
          return false;
        });
    const substantiveDraft = ['completa', 'parcial'].includes(written.draft.status);
    const claimsWithoutRelevantEvidence = unknown.length
      ? []
      : written.draft.claims.filter(
          (claim) =>
            !claimHasLexicalEvidence(
              claim.text,
              claim.evidence_ids.map(
                (evidenceId) =>
                  bundle.sourcesByEvidenceId.get(evidenceId) as NonNullable<
                    ReturnType<typeof bundle.sourcesByEvidenceId.get>
                  >
              )
            )
        );
    if (
      unknown.length ||
      claimsWithoutEvidence.length ||
      claimsWithIncompatiblePurpose.length ||
      (substantiveDraft && !candidateEvidenceIds.length) ||
      (substantiveDraft &&
        written.draft.claims.length > 0 &&
        claimsWithoutRelevantEvidence.length === written.draft.claims.length)
    ) {
      const reason = unknown.length
        ? `El redactor devolvió evidencias desconocidas: ${unknown.join(', ')}.`
        : claimsWithoutEvidence.length
          ? 'El redactor devolvió al menos una afirmación vacía o sin evidencia.'
          : claimsWithIncompatiblePurpose.length
            ? 'El redactor vinculó una afirmación a evidencia con una función jurídica incompatible.'
            : !candidateEvidenceIds.length
              ? 'El redactor no vinculó ninguna evidencia a la respuesta sustantiva.'
              : 'Al menos una afirmación no guarda relación suficiente con sus extractos literales.';
      return {
        strategy: this.id,
        status: 'error',
        text: '',
        sources: [],
        limits: [reason],
        cost,
        model: written.model,
        reasoning_effort: REASONING_EFFORT,
        latency_ms: Math.round(performance.now() - started),
        diagnostics: {
          authority_intent: authorityIntent,
          authority_match: 'not_requested',
          retrieval_filter: localAuthorityFilter(authorityIntent),
          retrieved_judgment_ids: [...new Set(retrieval.hits.map((hit) => hit.judgmentId))],
          citation_candidates: candidateEvidenceIds.length,
          citation_verified: 0,
          failure_code: 'evidence_validation',
          error_name: null,
        },
      };
    }
    const relevantClaims = written.draft.claims.filter(
      (claim) => !claimsWithoutRelevantEvidence.includes(claim)
    );
    const evidenceIds = [...new Set(relevantClaims.flatMap((claim) => claim.evidence_ids))];
    const sources = evidenceIds.map(
      (id) =>
        bundle.sourcesByEvidenceId.get(id) as NonNullable<
          ReturnType<typeof bundle.sourcesByEvidenceId.get>
        >
    );
    const sourceIndexByEvidenceId = new Map(
      evidenceIds.map((evidenceId, index) => [evidenceId, index + 1])
    );
    const claims = relevantClaims.map((claim) => ({
      text: claim.text.trim(),
      source_indexes: [...new Set(claim.evidence_ids)].map(
        (evidenceId) => sourceIndexByEvidenceId.get(evidenceId) as number
      ),
    }));
    const text = claims
      .map(
        (claim) => `- ${claim.text} ${claim.source_indexes.map((index) => `[${index}]`).join('')}`
      )
      .join('\n');
    const directAuthority = authorityMatch(
      authorityIntent,
      sources.map((source) => source.judgment_id)
    );
    const authorityLimit =
      authorityIntent && directAuthority === 'missing'
        ? `Las citas verificadas no proceden directamente del ${authorityLabel(authorityIntent)}.`
        : null;
    let finalStatus =
      retrieval.behavior === 'parcial' && written.draft.status === 'completa'
        ? 'parcial'
        : written.draft.status;
    if (authorityLimit && finalStatus === 'completa') finalStatus = 'parcial';
    if (claimsWithoutRelevantEvidence.length && finalStatus === 'completa') finalStatus = 'parcial';
    const relevanceLimit = claimsWithoutRelevantEvidence.length
      ? `Se retiró ${claimsWithoutRelevantEvidence.length} afirmación sin respaldo literal suficiente.`
      : null;
    return {
      strategy: this.id,
      status: finalStatus,
      text,
      sources,
      claims,
      limits: [
        ...retrievalLimits,
        ...written.draft.limits,
        ...(relevanceLimit ? [relevanceLimit] : []),
        ...(authorityLimit ? [authorityLimit] : []),
      ],
      cost,
      model: written.model,
      reasoning_effort: REASONING_EFFORT,
      latency_ms: Math.round(performance.now() - started),
      diagnostics: {
        authority_intent: authorityIntent,
        authority_match: directAuthority,
        retrieval_filter: localAuthorityFilter(authorityIntent),
        retrieved_judgment_ids: [...new Set(retrieval.hits.map((hit) => hit.judgmentId))],
        citation_candidates: candidateEvidenceIds.length,
        citation_verified: sources.length,
        failure_code: null,
        error_name: null,
      },
    };
  }
}

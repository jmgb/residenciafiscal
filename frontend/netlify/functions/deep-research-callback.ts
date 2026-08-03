import { verifyAlfredoSignature } from './deep-research/alfredo-client';
import {
  DEEP_RESEARCH_MODEL,
  DEEP_RESEARCH_OUTPUT_SCHEMA,
  DEEP_RESEARCH_REASONING_EFFORT,
  type DeepResearchOutput,
  type DeepResearchStore,
} from './deep-research/contracts';
import { createProductionDeepResearchStore } from './deep-research/store';

const MAX_BODY_BYTES = 250_000;

interface CallbackDependencies {
  secret: string;
  store: DeepResearchStore;
  verifySignature(
    secret: string,
    timestamp: string | null,
    signature: string | null,
    body: string
  ): Promise<boolean>;
}

const errorResponse = (status: number, error: string) =>
  Response.json({ error }, { status, headers: { 'cache-control': 'no-store' } });

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const validHash = (value: unknown): value is string =>
  typeof value === 'string' && /^[0-9a-f]{64}$/i.test(value);

const validMeasuredCost = (cost: unknown, measurement: unknown): boolean => {
  if (measurement === 'UNAVAILABLE') return cost === null || cost === undefined;
  return (
    (measurement === 'ACTUAL' || measurement === 'ESTIMATED') &&
    typeof cost === 'number' &&
    cost >= 0 &&
    Number.isSafeInteger(cost)
  );
};

const parseOutput = (value: unknown, jobId: string): DeepResearchOutput | null => {
  if (!isRecord(value)) return null;
  if (
    value.schema_version !== DEEP_RESEARCH_OUTPUT_SCHEMA ||
    value.job_id !== jobId ||
    value.request_id !== jobId ||
    !['completa', 'parcial', 'pregunta', 'abstención', 'error'].includes(String(value.status)) ||
    typeof value.text !== 'string' ||
    !Array.isArray(value.limits) ||
    !Array.isArray(value.claims) ||
    !Array.isArray(value.evidence) ||
    !['ACTUAL', 'ESTIMATED', 'UNAVAILABLE'].includes(String(value.cost_measurement)) ||
    !validMeasuredCost(value.cost_microusd, value.cost_measurement) ||
    typeof value.pricing_version !== 'string' ||
    value.pricing_version.trim().length < 1 ||
    typeof value.model !== 'string' ||
    value.model.trim().length < 1 ||
    value.model !== DEEP_RESEARCH_MODEL ||
    value.reasoning_effort !== DEEP_RESEARCH_REASONING_EFFORT ||
    typeof value.latency_ms !== 'number' ||
    value.latency_ms < 0 ||
    !Number.isSafeInteger(value.latency_ms)
  ) {
    return null;
  }
  const claims = value.claims.map((claim) => {
    if (
      !isRecord(claim) ||
      typeof claim.text !== 'string' ||
      !Array.isArray(claim.evidence_indexes)
    ) {
      return null;
    }
    if (
      !claim.evidence_indexes.every((index) => Number.isSafeInteger(index) && Number(index) > 0)
    ) {
      return null;
    }
    return { text: claim.text, evidenceIndexes: claim.evidence_indexes as number[] };
  });
  const evidence = value.evidence.map((item) => {
    if (
      !isRecord(item) ||
      typeof item.judgment_id !== 'string' ||
      !Number.isSafeInteger(item.page) ||
      Number(item.page) < 1 ||
      !validHash(item.source_sha256) ||
      typeof item.quote !== 'string' ||
      item.verification !== 'EXACT'
    ) {
      return null;
    }
    return {
      judgmentId: item.judgment_id,
      page: item.page,
      sourceSha256: item.source_sha256,
      quote: item.quote,
      verification: 'EXACT' as const,
    };
  });
  if (
    claims.some((claim) => claim === null) ||
    evidence.some((item) => item === null) ||
    claims.some((claim) => claim?.evidenceIndexes.length === 0) ||
    !value.limits.every((limit) => typeof limit === 'string')
  ) {
    return null;
  }
  if (
    (value.status === 'completa' || value.status === 'parcial') &&
    (claims.length === 0 || evidence.length === 0)
  ) {
    return null;
  }
  if (
    claims.some((claim) => claim?.evidenceIndexes.some((index) => index > evidence.length) === true)
  ) {
    return null;
  }
  const referencedEvidence = new Set(claims.flatMap((claim) => claim?.evidenceIndexes ?? []));
  const remappedIndexes = new Map<number, number>();
  const reconciledEvidence = evidence.flatMap((item, index) => {
    const originalIndex = index + 1;
    if (!referencedEvidence.has(originalIndex)) return [];
    remappedIndexes.set(originalIndex, remappedIndexes.size + 1);
    return [item];
  });
  const reconciledClaims = claims.map((claim) => ({
    ...claim,
    evidenceIndexes: claim?.evidenceIndexes.map((index) => remappedIndexes.get(index) as number),
  }));
  return {
    schemaVersion: DEEP_RESEARCH_OUTPUT_SCHEMA,
    jobId,
    requestId: value.request_id,
    status: value.status as DeepResearchOutput['status'],
    text: value.text,
    limits: value.limits as string[],
    claims: reconciledClaims as DeepResearchOutput['claims'],
    evidence: reconciledEvidence as DeepResearchOutput['evidence'],
    costMicrousd: typeof value.cost_microusd === 'number' ? value.cost_microusd : null,
    costMeasurement: value.cost_measurement as DeepResearchOutput['costMeasurement'],
    pricingVersion: value.pricing_version,
    model: DEEP_RESEARCH_MODEL,
    reasoningEffort: DEEP_RESEARCH_REASONING_EFFORT,
    latencyMs: value.latency_ms,
  };
};

export const createDeepResearchCallbackHandler =
  ({ secret, store, verifySignature }: CallbackDependencies) =>
  async (request: Request): Promise<Response> => {
    if (request.method !== 'POST') return errorResponse(405, 'Método no permitido');
    const declaredLength = Number(request.headers.get('content-length'));
    if (Number.isFinite(declaredLength) && declaredLength > MAX_BODY_BYTES) {
      return errorResponse(413, 'Payload demasiado grande');
    }
    const body = await request.text();
    if (new TextEncoder().encode(body).byteLength > MAX_BODY_BYTES)
      return errorResponse(413, 'Payload demasiado grande');
    const valid = await verifySignature(
      secret,
      request.headers.get('X-Alfredo-Timestamp'),
      request.headers.get('X-Alfredo-Signature'),
      body
    );
    if (!valid) return errorResponse(401, 'Firma inválida');
    let payload: unknown;
    try {
      payload = JSON.parse(body);
    } catch {
      return errorResponse(400, 'Callback inválido');
    }
    if (
      !isRecord(payload) ||
      typeof payload.job_id !== 'string' ||
      !/^[\w-]{1,128}$/.test(payload.job_id) ||
      typeof payload.status !== 'string'
    ) {
      return errorResponse(400, 'Callback inválido');
    }
    let output: DeepResearchOutput | null = null;
    if (
      payload.status === 'completed' &&
      payload.model === DEEP_RESEARCH_MODEL &&
      payload.reasoning_effort === DEEP_RESEARCH_REASONING_EFFORT &&
      typeof payload.final_text === 'string'
    ) {
      try {
        output = parseOutput(JSON.parse(payload.final_text), payload.job_id);
      } catch {
        output = null;
      }
    }
    const status =
      payload.status === 'completed' && output?.status === 'error'
        ? 'error'
        : payload.status === 'completed'
          ? output
            ? 'completed'
            : 'error'
          : payload.status === 'cancelled' || payload.status === 'canceled'
            ? 'cancelled'
            : payload.status === 'running'
              ? 'running'
              : 'error';
    const callbackStage = isRecord(payload.runtime) ? payload.runtime.stage : null;
    const stage =
      status === 'completed'
        ? 'completed'
        : status === 'cancelled'
          ? 'cancelled'
          : status === 'error'
            ? 'error'
            : callbackStage === 'searching' ||
                callbackStage === 'reading' ||
                callbackStage === 'verifying'
              ? callbackStage
              : 'reading';
    await store.update({
      jobId: payload.job_id,
      status,
      stage,
      result: status === 'completed' ? output : null,
      error: status === 'error' ? 'La salida de Alfredo no superó el contrato verificable.' : null,
    });
    return new Response(null, { status: 204, headers: { 'cache-control': 'no-store' } });
  };

const store = createProductionDeepResearchStore();
export default createDeepResearchCallbackHandler({
  secret: process.env.ALFREDO_HMAC_SECRET?.trim() || '',
  store: store ?? {
    async create() {
      throw new Error('unavailable');
    },
    async get() {
      return null;
    },
    async update() {},
    async cancel() {
      return false;
    },
  },
  verifySignature: (secret, timestamp, signature, body) =>
    verifyAlfredoSignature(secret, timestamp, signature, body),
});

export const config = {
  path: '/api/deep-research-callback',
  method: 'POST',
};

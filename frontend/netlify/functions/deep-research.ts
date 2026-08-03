import { submitDeepResearchJob } from './deep-research/alfredo-client';
import {
  DEEP_RESEARCH_OUTPUT_SCHEMA,
  DEEP_RESEARCH_PROFILE,
  type DeepResearchAlfredoPayload,
  type DeepResearchEnvironment,
  type DeepResearchStore,
  type DeepResearchSubmitResult,
} from './deep-research/contracts';
import { createProductionDeepResearchStore } from './deep-research/store';

const MAX_BODY_BYTES = 4_000;
const MAX_QUESTION_CHARS = 500;

interface StartInput {
  conversationId: string;
  comparisonId: string | null;
  countryPath: string;
  question: string;
}

interface StartDependencies {
  env: DeepResearchEnvironment;
  store: DeepResearchStore;
  submit(payload: DeepResearchAlfredoPayload): Promise<DeepResearchSubmitResult>;
}

const jsonError = (status: number, error: string) =>
  Response.json({ error }, { status, headers: { 'cache-control': 'no-store' } });

const validIdentifier = (value: unknown): value is string =>
  typeof value === 'string' && /^[\w-]{1,128}$/.test(value);

const validComparisonId = (value: unknown): value is string | null =>
  value === undefined ||
  value === null ||
  (typeof value === 'string' && /^chat-[\w-]{1,123}$/.test(value));

const validCountryPath = (value: unknown): value is string =>
  typeof value === 'string' && /^\/[a-z0-9-]{1,63}$/.test(value);

const parseInput = async (request: Request): Promise<StartInput | null> => {
  const declaredLength = Number(request.headers.get('content-length'));
  if (Number.isFinite(declaredLength) && declaredLength > MAX_BODY_BYTES) return null;
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_BODY_BYTES) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== 'object') return null;
  const value = parsed as Record<string, unknown>;
  if (
    !validIdentifier(value.conversation_id) ||
    !validComparisonId(value.comparison_id) ||
    !validCountryPath(value.country_path) ||
    typeof value.question !== 'string' ||
    value.question.trim().length < 1 ||
    value.question.trim().length > MAX_QUESTION_CHARS
  ) {
    return null;
  }
  return {
    conversationId: value.conversation_id,
    comparisonId: value.comparison_id === undefined ? null : value.comparison_id,
    countryPath: value.country_path,
    question: value.question.trim(),
  };
};

async function questionHash(question: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(question));
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, '0')).join('');
}

const taskFor = (input: StartInput, jobId: string, bundleId: string): string =>
  [
    'Ejecuta una investigación jurídica profunda offline para residencia fiscal española.',
    `job_id: ${jobId}`,
    `bundle_id: ${bundleId}`,
    `Pregunta del usuario: <pregunta>${input.question}</pregunta>`,
    '',
    'Usa exclusivamente el bundle inmutable indicado en el runtime.',
    'No uses internet, web search, repositorios, credenciales ni otros directorios.',
    'No escribas archivos. No muestres razonamiento interno ni cadena de pensamiento.',
    'Devuelve únicamente JSON válido que cumpla el output_schema solicitado.',
    `En el JSON final, usa exactamente job_id: ${jobId} y request_id: ${jobId}; no uses el bundle_id como request_id.`,
    'Cada afirmación sustantiva debe tener una evidencia literal verificable; si no basta, responde parcial, pregunta o abstención.',
  ].join('\n');

export const createDeepResearchHandler =
  ({ env, store, submit }: StartDependencies) =>
  async (request: Request): Promise<Response> => {
    if (request.method !== 'POST') return jsonError(405, 'Método no permitido');
    if (!env.enabled) return jsonError(503, 'Investigación profunda no disponible');
    const input = await parseInput(request);
    if (!input) return jsonError(400, 'Petición inválida');

    const jobId = `deep-${crypto.randomUUID()}`;
    try {
      await store.create({
        jobId,
        conversationId: input.conversationId,
        comparisonId: input.comparisonId,
        countryPath: input.countryPath,
        question: input.question,
        bundleId: env.bundleId,
      });
    } catch {
      return jsonError(503, 'Registro de investigación no disponible');
    }
    const payload: DeepResearchAlfredoPayload = {
      job_id: jobId,
      tenant_id: 'residenciafiscal',
      client_id: 'residenciafiscal',
      user_phone: `residenciafiscal:${input.conversationId}`,
      source_message_id: jobId,
      task_hash: await questionHash(input.question),
      task: taskFor(input, jobId, env.bundleId),
      target_id: 'codex',
      target_label: 'Codex',
      runtime: {
        target_id: 'codex',
        target_label: 'Codex',
        profile: DEEP_RESEARCH_PROFILE,
        sandbox: 'read-only',
        mode: 'exec_json',
        allowed_tools: [],
        output_schema: DEEP_RESEARCH_OUTPUT_SCHEMA,
        bundle_id: env.bundleId,
        egress: 'controller-only',
      },
      session_scope: 'job',
      session_id_to_resume: null,
      deadline_seconds: 900,
      context: {
        app: 'residenciafiscal',
        feature: 'deep_research',
        conversation_id: input.conversationId,
        comparison_id: input.comparisonId,
        country_path: input.countryPath,
        bundle_id: env.bundleId,
      },
      callback_url: env.callbackUrl,
    };
    try {
      const accepted = await submit(payload);
      if (accepted.jobId !== jobId || accepted.status !== 'queued') {
        throw new Error('Alfredo ha devuelto una aceptación incoherente');
      }
      return Response.json(
        { job_id: jobId, status: accepted.status },
        { status: 202, headers: { 'cache-control': 'no-store' } }
      );
    } catch {
      await store.update({
        jobId,
        status: 'error',
        stage: 'error',
        result: null,
        error: 'No se ha podido poner la investigación en cola.',
      });
      return jsonError(503, 'No se ha podido poner la investigación en cola');
    }
  };

const environmentFrom = (environment: NodeJS.ProcessEnv): DeepResearchEnvironment => {
  const alfredoJobsUrl = environment.ALFREDO_JOBS_URL?.trim() || '';
  const alfredoHmacSecret = environment.ALFREDO_HMAC_SECRET?.trim() || '';
  const callbackUrl = environment.DEEP_RESEARCH_CALLBACK_URL?.trim() || '';
  const bundleId = environment.DEEP_RESEARCH_BUNDLE_ID?.trim() || '';
  return {
    enabled:
      environment.DEEP_RESEARCH_ENABLED === 'true' &&
      alfredoJobsUrl.startsWith('https://') &&
      alfredoHmacSecret.length > 0 &&
      callbackUrl.startsWith('https://') &&
      bundleId.length > 0,
    alfredoJobsUrl,
    alfredoHmacSecret,
    callbackUrl,
    bundleId,
  };
};

const productionEnvironment = environmentFrom(process.env);
const productionStore = createProductionDeepResearchStore();

export default createDeepResearchHandler({
  env: productionEnvironment,
  store: productionStore ?? {
    async create() {
      throw new Error('deep research persistence unavailable');
    },
    async get() {
      return null;
    },
    async update() {},
    async cancel() {
      return false;
    },
  },
  submit: (payload) => submitDeepResearchJob(productionEnvironment, payload),
});

export const config = {
  path: '/api/deep-research',
  method: 'POST',
  rateLimit: { aggregateBy: ['ip', 'domain'], windowSize: 60, windowLimit: 2 },
};

export const DEEP_RESEARCH_PROFILE = 'residenciafiscal-deep-research-v2';
export const DEEP_RESEARCH_DRAFT_SCHEMA = 'residenciafiscal-deep-research-draft/2';
export const DEEP_RESEARCH_OUTPUT_SCHEMA = 'residenciafiscal-deep-research-output/2';
export const DEEP_RESEARCH_LEGACY_OUTPUT_SCHEMA = 'residenciafiscal-deep-research-output/1';
// Copia a mano del modelo de Codex (decisión del 2026-11-26), igual que
// src/deep_research_policy.py y Alfredo.
export const DEEP_RESEARCH_MODEL = 'gpt-6.2-sol';
export const DEEP_RESEARCH_REASONING_EFFORT = 'high';
// Resultados guardados con Luna declaran `max` (desde el 2026-10-23) o `high`
// (antes): siguen siendo legibles.
export type DeepResearchReasoningEffort = 'high' | 'max';
export interface DeepResearchCallbackContract {
  model: string;
  reasoningEffort: DeepResearchReasoningEffort;
}
// El callback acepta solo estos pares. Cambiar modelo o esfuerzo exige una
// transición: Alfredo admite los dos, Netlify envía el nuevo y su callback acepta
// los dos, y el antiguo se retira cuando no quede ningún job suyo en vuelo
// (deadline de 900 s). Ver docs/operations/DEEP_RESEARCH.md.
export const DEEP_RESEARCH_CALLBACK_CONTRACTS: readonly DeepResearchCallbackContract[] = [
  { model: DEEP_RESEARCH_MODEL, reasoningEffort: DEEP_RESEARCH_REASONING_EFFORT },
  // Transición del 2026-11-26: se retira cuando no quede ningún job de Luna en vuelo.
  { model: 'gpt-6-luna', reasoningEffort: 'max' },
];
export const DEEP_RESEARCH_ALLOWED_TOOLS = [
  'corpus.search_corpus',
  'corpus.read_case',
  'corpus.read_verbatim_page',
] as const;

export type DeepResearchStatus = 'queued' | 'running' | 'completed' | 'cancelled' | 'error';
export type DeepResearchStage =
  | 'searching'
  | 'reading'
  | 'verifying'
  | 'completed'
  | 'cancelled'
  | 'error';

export interface DeepResearchEvidence {
  judgmentId: string;
  page: number;
  sourceSha256: string;
  quote: string;
  verification: 'EXACT';
}

export interface DeepResearchClaim {
  text: string;
  evidenceIndexes: number[];
}

export interface DeepResearchOutput {
  schemaVersion: typeof DEEP_RESEARCH_OUTPUT_SCHEMA | typeof DEEP_RESEARCH_LEGACY_OUTPUT_SCHEMA;
  jobId: string;
  requestId: string;
  status: 'completa' | 'parcial' | 'pregunta' | 'abstención' | 'error';
  text: string;
  limits: string[];
  claims: DeepResearchClaim[];
  evidence: DeepResearchEvidence[];
  costMicrousd: number | null;
  costMeasurement: 'ACTUAL' | 'ESTIMATED' | 'UNAVAILABLE';
  pricingVersion: string;
  model: string;
  reasoningEffort: DeepResearchReasoningEffort;
  latencyMs: number;
}

export interface DeepResearchJobRecord {
  jobId: string;
  conversationId: string;
  comparisonId: string | null;
  status: DeepResearchStatus;
  stage: DeepResearchStage;
  result: DeepResearchOutput | null;
  error: string | null;
}

export interface DeepResearchStore {
  authorizeConversation(input: {
    conversationId: string;
    countryPath: string;
    conversationAccessHash: string;
  }): Promise<void>;
  create(input: {
    jobId: string;
    conversationId: string;
    comparisonId: string | null;
    countryPath: string;
    question: string;
    bundleId: string;
  }): Promise<DeepResearchJobRecord>;
  get(jobId: string, conversationId: string): Promise<DeepResearchJobRecord | null>;
  update(input: {
    jobId: string;
    status: DeepResearchStatus;
    stage: DeepResearchStage;
    result: DeepResearchOutput | null;
    error: string | null;
  }): Promise<void>;
  cancel(jobId: string, conversationId: string): Promise<boolean>;
}

export interface DeepResearchEnvironment {
  enabled: boolean;
  alfredoJobsUrl: string;
  alfredoHmacSecret: string;
  callbackUrl: string;
  bundleId: string;
}

export interface DeepResearchAlfredoPayload {
  job_id: string;
  tenant_id: 'residenciafiscal';
  client_id: 'residenciafiscal';
  user_phone: string;
  source_message_id: string;
  task_hash: string;
  task: string;
  target_id: 'codex';
  target_label: 'Codex';
  runtime: {
    target_id: 'codex';
    target_label: 'Codex';
    profile: typeof DEEP_RESEARCH_PROFILE;
    model: typeof DEEP_RESEARCH_MODEL;
    reasoning_effort: typeof DEEP_RESEARCH_REASONING_EFFORT;
    sandbox: 'read-only';
    mode: 'exec_json';
    allowed_tools: [...typeof DEEP_RESEARCH_ALLOWED_TOOLS];
    output_schema: typeof DEEP_RESEARCH_DRAFT_SCHEMA;
    bundle_id: string;
    egress: 'provider-only';
  };
  session_scope: 'job';
  session_id_to_resume: null;
  deadline_seconds: 900;
  context: {
    app: 'residenciafiscal';
    feature: 'deep_research';
    conversation_id: string;
    comparison_id: string | null;
    country_path: string;
    bundle_id: string;
  };
  callback_url: string;
}

export interface DeepResearchSubmitResult {
  jobId: string;
  status: string;
}

export const DEEP_RESEARCH_PROFILE = 'residenciafiscal-deep-research-v1';
export const DEEP_RESEARCH_OUTPUT_SCHEMA = 'residenciafiscal-deep-research-output/1';

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
  schemaVersion: typeof DEEP_RESEARCH_OUTPUT_SCHEMA;
  jobId: string;
  requestId: string;
  status: 'completa' | 'parcial' | 'pregunta' | 'abstención' | 'error';
  text: string;
  limits: string[];
  claims: DeepResearchClaim[];
  evidence: DeepResearchEvidence[];
  costMicrousd: number | null;
  costMeasurement: 'ACTUAL' | 'ESTIMATED' | 'UNAVAILABLE';
  model: string;
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
    sandbox: 'read-only';
    mode: 'exec_json';
    allowed_tools: [];
    output_schema: typeof DEEP_RESEARCH_OUTPUT_SCHEMA;
    bundle_id: string;
    egress: 'controller-only';
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

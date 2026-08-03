import { cancelDeepResearchJob } from './deep-research/alfredo-client';
import type { DeepResearchEnvironment, DeepResearchStore } from './deep-research/contracts';
import { createProductionDeepResearchStore } from './deep-research/store';

interface CancelDependencies {
  env: DeepResearchEnvironment;
  store: DeepResearchStore;
  cancelRemote(environment: DeepResearchEnvironment, jobId: string): Promise<boolean>;
}

const errorResponse = (status: number, error: string) =>
  Response.json({ error }, { status, headers: { 'cache-control': 'no-store' } });

export const createDeepResearchCancelHandler =
  ({ env, store, cancelRemote }: CancelDependencies) =>
  async (request: Request): Promise<Response> => {
    if (request.method !== 'POST') return errorResponse(405, 'Método no permitido');
    if (!env.enabled) return errorResponse(503, 'Investigación profunda no disponible');
    let input: unknown;
    try {
      input = await request.json();
    } catch {
      return errorResponse(400, 'Petición inválida');
    }
    if (!input || typeof input !== 'object') return errorResponse(400, 'Petición inválida');
    const value = input as Record<string, unknown>;
    if (
      typeof value.job_id !== 'string' ||
      !/^[\w-]{1,128}$/.test(value.job_id) ||
      typeof value.conversation_id !== 'string' ||
      !/^[\w-]{1,128}$/.test(value.conversation_id)
    ) {
      return errorResponse(400, 'Petición inválida');
    }
    const job = await store.get(value.job_id, value.conversation_id);
    if (!job) return errorResponse(404, 'Investigación no encontrada');
    if (job.status === 'completed' || job.status === 'cancelled' || job.status === 'error') {
      return errorResponse(409, 'La investigación ya ha terminado');
    }
    try {
      const remoteAccepted = await cancelRemote(env, value.job_id);
      if (!remoteAccepted) return errorResponse(503, 'Alfredo no ha aceptado la cancelación');
      await store.cancel(value.job_id, value.conversation_id);
      return Response.json(
        { job_id: value.job_id, status: 'cancelled' },
        { status: 202, headers: { 'cache-control': 'no-store' } }
      );
    } catch {
      return errorResponse(503, 'No se ha podido cancelar la investigación');
    }
  };

const environmentFrom = (environment: NodeJS.ProcessEnv): DeepResearchEnvironment => ({
  enabled: environment.DEEP_RESEARCH_ENABLED === 'true',
  alfredoJobsUrl: environment.ALFREDO_JOBS_URL?.trim() || '',
  alfredoHmacSecret: environment.ALFREDO_HMAC_SECRET?.trim() || '',
  callbackUrl: environment.DEEP_RESEARCH_CALLBACK_URL?.trim() || '',
  bundleId: environment.DEEP_RESEARCH_BUNDLE_ID?.trim() || '',
});
const productionEnvironment = environmentFrom(process.env);
const store = createProductionDeepResearchStore();
export default createDeepResearchCancelHandler({
  env: productionEnvironment,
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
  cancelRemote: (environment, jobId) => cancelDeepResearchJob(environment, jobId),
});

export const config = {
  path: '/api/deep-research-cancel',
  method: 'POST',
  rateLimit: { aggregateBy: ['ip', 'domain'], windowSize: 60, windowLimit: 5 },
};

import type { DeepResearchStore } from './deep-research/contracts';
import { createProductionDeepResearchStore } from './deep-research/store';

const errorResponse = (status: number, error: string) =>
  Response.json({ error }, { status, headers: { 'cache-control': 'no-store' } });

export interface DeepResearchStatusDependencies {
  store: DeepResearchStore;
}

export const createDeepResearchStatusHandler =
  ({ store }: DeepResearchStatusDependencies) =>
  async (request: Request): Promise<Response> => {
    if (request.method !== 'GET') return errorResponse(405, 'Método no permitido');
    const url = new URL(request.url);
    const jobId = url.searchParams.get('job_id');
    const conversationId = url.searchParams.get('conversation_id');
    if (
      !jobId ||
      !/^[\w-]{1,128}$/.test(jobId) ||
      !conversationId ||
      !/^[\w-]{1,128}$/.test(conversationId)
    ) {
      return errorResponse(400, 'Petición inválida');
    }
    try {
      const job = await store.get(jobId, conversationId);
      if (!job) return errorResponse(404, 'Investigación no encontrada');
      return Response.json(
        {
          job_id: job.jobId,
          comparison_id: job.comparisonId,
          status: job.status,
          stage: job.stage,
          result: job.result,
          error: job.error,
        },
        { headers: { 'cache-control': 'no-store' } }
      );
    } catch {
      return errorResponse(503, 'Estado no disponible');
    }
  };

const store = createProductionDeepResearchStore();
export default createDeepResearchStatusHandler({
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
});

export const config = {
  path: '/api/deep-research-status',
  method: 'GET',
  rateLimit: { aggregateBy: ['ip', 'domain'], windowSize: 60, windowLimit: 30 },
};

import type { DeepResearchJob } from '@/types/chat';

interface StartResponse {
  job_id: string;
  status: string;
}

interface StatusResponse {
  job_id: string;
  comparison_id: string | null;
  status: DeepResearchJob['status'];
  stage: DeepResearchJob['stage'];
  result: DeepResearchJob['result'];
  error: string | null;
}

export class DeepResearchRequestError extends Error {
  constructor(readonly status: number) {
    super('Investigación profunda no disponible');
    this.name = 'DeepResearchRequestError';
  }
}

const jsonRequest = async <T>(url: string, init: RequestInit): Promise<T> => {
  const response = await fetch(url, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init.headers ?? {}) },
  });
  if (!response.ok) throw new DeepResearchRequestError(response.status);
  return (await response.json()) as T;
};

export async function startDeepResearch(input: {
  conversationId: string;
  comparisonId?: string | null;
  countryPath: string;
  question: string;
}): Promise<{ jobId: string; status: string }> {
  const response = await jsonRequest<StartResponse>('/api/deep-research', {
    method: 'POST',
    body: JSON.stringify({
      conversation_id: input.conversationId,
      comparison_id: input.comparisonId ?? null,
      country_path: input.countryPath,
      question: input.question,
    }),
  });
  return { jobId: response.job_id, status: response.status };
}

export async function getDeepResearchStatus(
  jobId: string,
  conversationId: string
): Promise<DeepResearchJob> {
  const query = new URLSearchParams({ job_id: jobId, conversation_id: conversationId });
  const response = await jsonRequest<StatusResponse>(`/api/deep-research-status?${query}`, {
    method: 'GET',
  });
  return {
    jobId: response.job_id,
    comparisonId: response.comparison_id,
    status: response.status,
    stage: response.stage,
    result: response.result,
    error: response.error,
  };
}

export async function cancelDeepResearch(jobId: string, conversationId: string): Promise<void> {
  await jsonRequest('/api/deep-research-cancel', {
    method: 'POST',
    body: JSON.stringify({ job_id: jobId, conversation_id: conversationId }),
  });
}

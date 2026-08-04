import { describe, expect, it } from 'vitest';
import {
  mergeDeepResearchPoll,
  messagePatchForDeepResearchStatus,
  withDeepResearchCancelError,
} from '@/components/chat/useDeepResearch';
import type { DeepResearchJob } from '@/types/chat';

describe('deep research assistant message', () => {
  it('copies the completed Codex output into the assistant message content', () => {
    const job: DeepResearchJob = {
      jobId: 'deep-job-1',
      status: 'completed',
      stage: 'completed',
      result: {
        schemaVersion: 'residenciafiscal-deep-research-output/2',
        jobId: 'deep-job-1',
        requestId: 'deep-job-1',
        status: 'completa',
        text: 'Respuesta final de Codex.',
        limits: [],
        claims: [],
        evidence: [],
        costMicrousd: null,
        costMeasurement: 'UNAVAILABLE',
        pricingVersion: 'test-catalog',
        model: 'gpt-5-codex',
        reasoningEffort: 'high',
        latencyMs: 4200,
      },
    };

    expect(messagePatchForDeepResearchStatus(job)).toEqual({
      content: 'Respuesta final de Codex.',
      deepResearch: job,
    });
  });

  it('keeps active and failed jobs as metadata without inventing assistant content', () => {
    const job: DeepResearchJob = {
      jobId: 'deep-job-1',
      status: 'running',
      stage: 'reading',
      result: null,
    };

    expect(messagePatchForDeepResearchStatus(job)).toEqual({ deepResearch: job });
  });

  it('keeps a cancellation error visible until cancellation succeeds or the job finishes', () => {
    const running: DeepResearchJob = {
      jobId: 'deep-job-1',
      status: 'running',
      stage: 'reading',
      result: null,
    };
    const failedCancellation = withDeepResearchCancelError(running);

    expect(failedCancellation.error).toBe('No se ha podido cancelar la investigación.');
    expect(mergeDeepResearchPoll(failedCancellation, running).error).toBe(
      'No se ha podido cancelar la investigación.'
    );
    expect(
      mergeDeepResearchPoll(failedCancellation, {
        ...running,
        status: 'cancelled',
        stage: 'cancelled',
      }).error
    ).toBeUndefined();
  });
});

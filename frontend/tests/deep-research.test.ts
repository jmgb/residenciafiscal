import { afterEach, describe, expect, it, vi } from 'vitest';
import { createDeepResearchHandler } from '../netlify/functions/deep-research';
import { verifyAlfredoSignature } from '../netlify/functions/deep-research/alfredo-client';
import type {
  DeepResearchJobRecord,
  DeepResearchStore,
} from '../netlify/functions/deep-research/contracts';
import { createDeepResearchCallbackHandler } from '../netlify/functions/deep-research-callback';
import { createDeepResearchCancelHandler } from '../netlify/functions/deep-research-cancel';
import { createDeepResearchStatusHandler } from '../netlify/functions/deep-research-status';

const record: DeepResearchJobRecord = {
  jobId: 'deep-job-1',
  conversationId: 'conversation-1',
  comparisonId: 'chat-comparison-1',
  status: 'queued',
  stage: 'searching',
  result: null,
  error: null,
};

function createStore(): DeepResearchStore {
  return {
    create: vi.fn(async () => record),
    get: vi.fn(async () => record),
    update: vi.fn(async () => undefined),
    cancel: vi.fn(async () => true),
  };
}

const env = {
  enabled: true,
  alfredoJobsUrl: 'https://alfredo.example/jobs',
  alfredoHmacSecret: 'secret',
  callbackUrl: 'https://residenciafiscal.example/api/deep-research-callback',
  bundleId: 'rollout-106',
};

afterEach(() => vi.restoreAllMocks());

describe('deep research HTTP contract', () => {
  it('creates an authenticated Codex job without adding it to A/B', async () => {
    const store = createStore();
    const submit = vi.fn(async (payload: { job_id: string }) => ({
      jobId: payload.job_id,
      status: 'queued',
    }));
    const handler = createDeepResearchHandler({ env, store, submit });

    const response = await handler(
      new Request('https://residenciafiscal.example/api/deep-research', {
        method: 'POST',
        body: JSON.stringify({
          conversation_id: 'conversation-1',
          comparison_id: 'chat-comparison-1',
          country_path: '/espana',
          question: '¿Cómo se acredita la residencia fiscal?',
        }),
      })
    );

    expect(response.status).toBe(202);
    expect(await response.json()).toMatchObject({
      job_id: expect.stringMatching(/^deep-/),
      status: 'queued',
    });
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({
        job_id: expect.stringMatching(/^deep-/),
        context: expect.objectContaining({ comparison_id: 'chat-comparison-1' }),
        target_id: 'codex',
        callback_url: env.callbackUrl,
        runtime: expect.objectContaining({
          profile: 'residenciafiscal-deep-research-v1',
          sandbox: 'read-only',
          mode: 'exec_json',
          output_schema: 'residenciafiscal-deep-research-output/1',
        }),
      })
    );
    const submitted = submit.mock.calls[0][0] as {
      job_id: string;
      task: string;
    };
    expect(submitted.task).toContain(`job_id: ${submitted.job_id}`);
    expect(submitted.task).toContain(`request_id: ${submitted.job_id}`);
  });

  it('fails closed if Alfredo acknowledges a different job identifier', async () => {
    const store = createStore();
    const handler = createDeepResearchHandler({
      env,
      store,
      submit: vi.fn(async () => ({ jobId: 'different-job', status: 'queued' })),
    });

    const response = await handler(
      new Request('https://residenciafiscal.example/api/deep-research', {
        method: 'POST',
        body: JSON.stringify({
          conversation_id: 'conversation-1',
          comparison_id: null,
          country_path: '/espana',
          question: '¿Cómo se acredita la residencia fiscal?',
        }),
      })
    );

    expect(response.status).toBe(503);
    expect(store.update).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'error', stage: 'error' })
    );
  });

  it('rejects malformed jobs before contacting Alfredo', async () => {
    const submit = vi.fn();
    const handler = createDeepResearchHandler({ env, store: createStore(), submit });

    const response = await handler(
      new Request('https://residenciafiscal.example/api/deep-research', {
        method: 'POST',
        body: JSON.stringify({ conversation_id: 'bad space', question: '' }),
      })
    );

    expect(response.status).toBe(400);
    expect(submit).not.toHaveBeenCalled();
  });

  it('accepts a signed Alfredo callback and exposes only the reconciled result', async () => {
    const store = createStore();
    const body = JSON.stringify({
      job_id: 'deep-job-1',
      status: 'completed',
      final_text: JSON.stringify({
        schema_version: 'residenciafiscal-deep-research-output/1',
        job_id: 'deep-job-1',
        request_id: 'deep-job-1',
        status: 'completa',
        text: 'Respuesta verificada.',
        limits: [],
        claims: [{ text: 'Afirmación', evidence_indexes: [1] }],
        evidence: [
          {
            judgment_id: 'sts-1',
            page: 3,
            source_sha256: 'a'.repeat(64),
            quote: 'Cita literal',
            verification: 'EXACT',
          },
        ],
        cost_microusd: 1200,
        cost_measurement: 'ACTUAL',
        model: 'gpt-5.6',
        latency_ms: 4200,
      }),
    });
    const handler = createDeepResearchCallbackHandler({
      secret: 'secret',
      store,
      verifySignature: vi.fn(async () => true),
    });

    const response = await handler(
      new Request('https://residenciafiscal.example/api/deep-research-callback', {
        method: 'POST',
        body,
        headers: {
          'X-Alfredo-Timestamp': '1770000000',
          'X-Alfredo-Signature': 'valid',
        },
      })
    );

    expect(response.status).toBe(204);
    expect(store.update).toHaveBeenCalledWith(
      expect.objectContaining({
        jobId: 'deep-job-1',
        status: 'completed',
        result: expect.objectContaining({ text: 'Respuesta verificada.' }),
      })
    );
  });

  it('does not reveal a job belonging to another conversation', async () => {
    const store = createStore();
    store.get = vi.fn(async () => null);
    const handler = createDeepResearchStatusHandler({ store });

    const response = await handler(
      new Request(
        'https://residenciafiscal.example/api/deep-research-status?job_id=deep-job-1&conversation_id=other'
      )
    );

    expect(response.status).toBe(404);
  });

  it('rejects a completed callback whose claim points outside its evidence list', async () => {
    const store = createStore();
    const body = JSON.stringify({
      job_id: 'deep-job-1',
      status: 'completed',
      final_text: JSON.stringify({
        schema_version: 'residenciafiscal-deep-research-output/1',
        job_id: 'deep-job-1',
        request_id: 'deep-job-1',
        status: 'completa',
        text: 'Respuesta.',
        limits: [],
        claims: [{ text: 'Afirmación', evidence_indexes: [2] }],
        evidence: [
          {
            judgment_id: 'sts-1',
            page: 3,
            source_sha256: 'a'.repeat(64),
            quote: 'Cita literal',
            verification: 'EXACT',
          },
        ],
        cost_microusd: 1200,
        cost_measurement: 'ACTUAL',
        model: 'gpt-5.6',
        latency_ms: 4200,
      }),
    });
    const handler = createDeepResearchCallbackHandler({
      secret: 'secret',
      store,
      verifySignature: vi.fn(async () => true),
    });

    const response = await handler(
      new Request('https://residenciafiscal.example/api/deep-research-callback', {
        method: 'POST',
        body,
        headers: {
          'X-Alfredo-Timestamp': '1770000000',
          'X-Alfredo-Signature': 'valid',
        },
      })
    );

    expect(response.status).toBe(204);
    expect(store.update).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'error', result: null })
    );
  });

  it('rejects a substantive completed callback without claims or evidence', async () => {
    const store = createStore();
    const body = JSON.stringify({
      job_id: 'deep-job-1',
      status: 'completed',
      final_text: JSON.stringify({
        schema_version: 'residenciafiscal-deep-research-output/1',
        job_id: 'deep-job-1',
        request_id: 'deep-job-1',
        status: 'completa',
        text: 'Respuesta sin respaldo.',
        limits: [],
        claims: [],
        evidence: [],
        cost_microusd: 1200,
        cost_measurement: 'ACTUAL',
        model: 'gpt-5.6',
        latency_ms: 4200,
      }),
    });
    const handler = createDeepResearchCallbackHandler({
      secret: 'secret',
      store,
      verifySignature: vi.fn(async () => true),
    });

    const response = await handler(
      new Request('https://residenciafiscal.example/api/deep-research-callback', {
        method: 'POST',
        body,
      })
    );

    expect(response.status).toBe(204);
    expect(store.update).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'error', result: null })
    );
  });

  it('rejects a callback whose cost contradicts its measurement', async () => {
    const store = createStore();
    const body = JSON.stringify({
      job_id: 'deep-job-1',
      status: 'completed',
      final_text: JSON.stringify({
        schema_version: 'residenciafiscal-deep-research-output/1',
        job_id: 'deep-job-1',
        request_id: 'deep-job-1',
        status: 'pregunta',
        text: 'Faltan hechos.',
        limits: [],
        claims: [],
        evidence: [],
        cost_microusd: null,
        cost_measurement: 'ACTUAL',
        model: 'gpt-5.6',
        latency_ms: 4200,
      }),
    });
    const handler = createDeepResearchCallbackHandler({
      secret: 'secret',
      store,
      verifySignature: vi.fn(async () => true),
    });

    await handler(
      new Request('https://residenciafiscal.example/api/deep-research-callback', {
        method: 'POST',
        body,
      })
    );

    expect(store.update).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'error', result: null })
    );
  });

  it('cancels a queued job through Alfredo and records the terminal state', async () => {
    const store = createStore();
    const cancelRemote = vi.fn(async () => true);
    const handler = createDeepResearchCancelHandler({
      env,
      store,
      cancelRemote,
    });

    const response = await handler(
      new Request('https://residenciafiscal.example/api/deep-research-cancel', {
        method: 'POST',
        body: JSON.stringify({ job_id: 'deep-job-1', conversation_id: 'conversation-1' }),
      })
    );

    expect(response.status).toBe(202);
    expect(cancelRemote).toHaveBeenCalledWith(env, 'deep-job-1');
    expect(store.cancel).toHaveBeenCalledWith('deep-job-1', 'conversation-1');
  });

  it('does not report cancellation when completion wins the persistence race', async () => {
    const store = createStore();
    store.cancel = vi.fn(async () => false);
    const handler = createDeepResearchCancelHandler({
      env,
      store,
      cancelRemote: vi.fn(async () => true),
    });

    const response = await handler(
      new Request('https://residenciafiscal.example/api/deep-research-cancel', {
        method: 'POST',
        body: JSON.stringify({ job_id: 'deep-job-1', conversation_id: 'conversation-1' }),
      })
    );

    expect(response.status).toBe(409);
  });

  it('never accepts callback signatures made with an empty secret', async () => {
    const body = '{}';
    const timestamp = String(Math.floor(Date.now() / 1000));

    expect(await verifyAlfredoSignature('', timestamp, '0'.repeat(64), body)).toBe(false);
  });
});

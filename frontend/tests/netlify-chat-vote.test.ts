import { describe, expect, it, vi } from 'vitest';
import {
  type ChatVoteDependencies,
  config,
  createChatVoteHandler,
} from '../netlify/functions/chat-vote';

const request = (body: unknown) =>
  new Request('https://residenciafiscal.org/api/chat-vote', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });

const dependencies = (overrides: Partial<ChatVoteDependencies> = {}): ChatVoteDependencies => ({
  enabled: true,
  vote: vi.fn(async () => true),
  ...overrides,
});

describe('Netlify Function /api/chat-vote', () => {
  it('declara una ruta POST con rate limit', () => {
    expect(config).toMatchObject({
      path: '/api/chat-vote',
      method: 'POST',
      rateLimit: { aggregateBy: ['ip', 'domain'], windowSize: 60, windowLimit: 10 },
    });
  });

  it('registra una opción ciega y un motivo cerrado', async () => {
    const deps = dependencies();
    const response = await createChatVoteHandler(deps)(
      request({
        request_id: 'chat-123e4567-e89b-12d3-a456-426614174000',
        verdict: 'a',
        reason: 'better_grounding',
      })
    );

    expect(response.status).toBe(204);
    expect(deps.vote).toHaveBeenCalledWith({
      requestId: 'chat-123e4567-e89b-12d3-a456-426614174000',
      verdict: 'a',
      reason: 'better_grounding',
    });
  });

  it('acepta C como opción cerrada del experimento ampliado', async () => {
    const deps = dependencies();
    const response = await createChatVoteHandler(deps)(
      request({
        request_id: 'chat-123e4567-e89b-12d3-a456-426614174000',
        verdict: 'c',
        reason: 'better_grounding',
      })
    );

    expect(response.status).toBe(204);
    expect(deps.vote).toHaveBeenCalledWith({
      requestId: 'chat-123e4567-e89b-12d3-a456-426614174000',
      verdict: 'c',
      reason: 'better_grounding',
    });
  });

  it('rechaza texto libre y valores fuera del catálogo', async () => {
    const deps = dependencies();
    const response = await createChatVoteHandler(deps)(
      request({
        request_id: 'chat-123e4567-e89b-12d3-a456-426614174000',
        verdict: 'a',
        reason: 'mi caso fiscal contiene datos personales',
      })
    );

    expect(response.status).toBe(400);
    expect(deps.vote).not.toHaveBeenCalled();
  });

  it('responde conflicto si la petición ya fue votada', async () => {
    const response = await createChatVoteHandler(dependencies({ vote: vi.fn(async () => false) }))(
      request({
        request_id: 'chat-123e4567-e89b-12d3-a456-426614174000',
        verdict: 'tie',
        reason: 'no_preference',
      })
    );

    expect(response.status).toBe(409);
  });
});

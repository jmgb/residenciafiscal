import { beforeEach, describe, expect, it, vi } from 'vitest';

const { createClient } = vi.hoisted(() => ({
  createClient: vi.fn(() => ({ rpc: vi.fn() })),
}));

vi.mock('@supabase/supabase-js', () => ({ createClient }));
vi.mock('@google/genai', () => ({
  GoogleGenAI: class GoogleGenAI {
    interactions = { create: vi.fn() };
  },
}));
vi.mock('openai', () => ({
  default: class OpenAI {
    responses = { create: vi.fn() };
  },
}));

import { createProductionDependencies } from '../netlify/functions/chat/composition';
import { SupabaseChatStore } from '../netlify/functions/chat/supabase-chat-store';

const experiment = {
  experiment_version: 'test',
  deployed_commit: 'test',
  comparison_schema_version: 'residenciafiscal-chat-comparison/1',
  structured_corpus_version: 'test',
  structured_prompt_version: 'test',
  file_search_store: 'fileSearchStores/test',
  file_search_prompt_version: 'test',
} as const;

const environment = {
  CHAT_COMPARISON_ENABLED: 'true',
  OPENAI_API_KEY: 'openai-test',
  GEMINI_API_KEY: 'gemini-test',
  CHAT_FILE_SEARCH_STORE_NAME: 'fileSearchStores/test',
  CHAT_FILE_SEARCH_MODEL: 'gemini-3.5-flash-lite',
  CHAT_DEADLINE_MS: '52000',
  SUPABASE_URL: 'https://project.supabase.co',
  SUPABASE_SECRET_KEY: 'sb_secret_test',
} as NodeJS.ProcessEnv;

describe('chat sin presupuesto monetario global', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('mantiene la Function habilitada sin variables de presupuesto', () => {
    const dependencies = createProductionDependencies(environment);

    expect(dependencies.enabled).toBe(true);
  });

  it('registra una consulta sin reservar dinero', async () => {
    const rpc = vi.fn(async () => ({
      data: { request_id: 'chat-request-1', created: true },
      error: null,
    }));
    const store = new SupabaseChatStore({ rpc }, experiment);

    await expect(
      store.record({
        requestId: 'chat-request-1',
        conversationId: 'conversation-1',
        userMessageId: 'message-1',
        countryPath: '/espana',
        question: 'Pregunta',
      })
    ).resolves.toEqual({ requestId: 'chat-request-1' });

    expect(rpc).toHaveBeenCalledWith('create_chat_request', {
      p_request_id: 'chat-request-1',
      p_conversation_id: 'conversation-1',
      p_user_message_id: 'message-1',
      p_country_path: '/espana',
      p_question: 'Pregunta',
      p_experiment: experiment,
    });
  });
});

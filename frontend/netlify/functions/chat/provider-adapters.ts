import { GoogleGenAI } from '@google/genai';
import OpenAI from 'openai';
import type {
  StructuredDraft,
  StructuredWriter,
  StructuredWriterResult,
} from './current-structured-strategy';
import type {
  GeminiFileSearchOptions,
  GeminiInteractionInput,
  Interaction,
} from './file-search-strategy';

const structuredDraftSchema = {
  type: 'object',
  additionalProperties: false,
  required: ['status', 'answer', 'limits', 'evidence_ids'],
  properties: {
    status: { type: 'string', enum: ['completa', 'parcial', 'pregunta', 'abstención'] },
    answer: { type: 'string' },
    limits: { type: 'array', items: { type: 'string' } },
    evidence_ids: { type: 'array', items: { type: 'string', pattern: '^E[0-9]+$' } },
  },
};

const fileSearchDraftSchema = {
  type: 'object',
  additionalProperties: false,
  required: ['status', 'answer', 'limits'],
  properties: {
    status: { type: 'string', enum: ['completa', 'parcial', 'pregunta', 'abstención'] },
    answer: { type: 'string' },
    limits: { type: 'array', items: { type: 'string' } },
  },
};

const isStructuredDraft = (value: unknown): value is StructuredDraft => {
  if (!value || typeof value !== 'object') return false;
  const draft = value as Record<string, unknown>;
  return (
    ['completa', 'parcial', 'pregunta', 'abstención'].includes(String(draft.status)) &&
    typeof draft.answer === 'string' &&
    Array.isArray(draft.limits) &&
    draft.limits.every((item) => typeof item === 'string') &&
    Array.isArray(draft.evidence_ids) &&
    draft.evidence_ids.every((item) => typeof item === 'string' && /^E[0-9]+$/.test(item))
  );
};

export const createOpenAIWriter = (apiKey: string): StructuredWriter => {
  const client = new OpenAI({ apiKey, maxRetries: 0, timeout: 50_000 });
  return {
    async write(input): Promise<StructuredWriterResult> {
      const response = await client.responses.create(
        {
          model: input.model,
          instructions: input.systemPrompt,
          input: input.userPrompt,
          reasoning: { effort: input.reasoningEffort },
          max_output_tokens: 4_000,
          store: false,
          metadata: { request_id: input.requestId },
          text: {
            format: {
              type: 'json_schema',
              name: 'structured_legal_answer',
              strict: true,
              schema: structuredDraftSchema,
            },
          },
        },
        { signal: input.signal }
      );
      const parsed = JSON.parse(response.output_text) as unknown;
      if (!isStructuredDraft(parsed)) throw new Error('Salida OpenAI inválida');
      return {
        draft: parsed,
        usage: {
          input_tokens: response.usage?.input_tokens ?? 0,
          output_tokens: response.usage?.output_tokens ?? 0,
          complete: response.usage != null,
        },
        model: response.model,
      };
    },
  };
};

export const createGeminiInteraction = (apiKey: string): GeminiFileSearchOptions['interact'] => {
  const client = new GoogleGenAI({ apiKey });
  return async (input: GeminiInteractionInput, signal: AbortSignal): Promise<Interaction> =>
    (await client.interactions.create(
      {
        model: input.model,
        input: input.prompt,
        tools: [
          {
            type: 'file_search',
            file_search_store_names: [input.storeName],
          },
        ],
        response_format: {
          type: 'text',
          mime_type: 'application/json',
          schema: fileSearchDraftSchema,
        },
        generation_config: { max_output_tokens: 2_000 },
        store: false,
      },
      {
        maxRetries: 0,
        timeout: 50_000,
        fetchOptions: { signal },
      }
    )) as unknown as Interaction;
};

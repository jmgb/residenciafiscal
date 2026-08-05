import { GoogleGenAI } from '@google/genai';
import OpenAI from 'openai';
import { ChatDiagnosticError, providerDiagnostic } from './chat-diagnostics';
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
  required: ['status', 'claims', 'limits'],
  properties: {
    status: { type: 'string', enum: ['completa', 'parcial', 'pregunta', 'abstención'] },
    limits: { type: 'array', items: { type: 'string' } },
    claims: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['kind', 'text', 'evidence_ids'],
        properties: {
          kind: {
            type: 'string',
            enum: [
              'party_argument',
              'judicial_assessment',
              'legal_rule',
              'holding',
              'procedural_power',
            ],
          },
          text: { type: 'string' },
          evidence_ids: {
            type: 'array',
            items: { type: 'string', pattern: '^E[0-9]+$' },
          },
        },
      },
    },
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
    Array.isArray(draft.limits) &&
    draft.limits.every((item) => typeof item === 'string') &&
    Array.isArray(draft.claims) &&
    draft.claims.every(
      (item) =>
        item &&
        typeof item === 'object' &&
        [
          'party_argument',
          'judicial_assessment',
          'legal_rule',
          'holding',
          'procedural_power',
        ].includes(String((item as { kind?: unknown }).kind)) &&
        typeof (item as { text?: unknown }).text === 'string' &&
        Array.isArray((item as { evidence_ids?: unknown }).evidence_ids) &&
        ((item as { evidence_ids: unknown[] }).evidence_ids as unknown[]).every(
          (evidenceId) => typeof evidenceId === 'string' && /^E[0-9]+$/.test(evidenceId)
        )
    )
  );
};

export const createOpenAIWriter = (apiKey: string): StructuredWriter => {
  const client = new OpenAI({ apiKey, maxRetries: 0, timeout: 50_000 });
  return {
    async write(input): Promise<StructuredWriterResult> {
      try {
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
        if (!isStructuredDraft(parsed)) throw new Error('invalid structured response');
        return {
          draft: parsed,
          usage: {
            input_tokens: response.usage?.input_tokens ?? 0,
            output_tokens: response.usage?.output_tokens ?? 0,
            complete: response.usage != null,
          },
          model: response.model,
        };
      } catch (error) {
        if (error instanceof ChatDiagnosticError) throw error;
        throw new ChatDiagnosticError(
          'OpenAI no disponible',
          providerDiagnostic('openai', 'responses.create', error)
        );
      }
    },
  };
};

export const createGeminiInteraction = (apiKey: string): GeminiFileSearchOptions['interact'] => {
  const client = new GoogleGenAI({ apiKey });
  return async (input: GeminiInteractionInput, signal: AbortSignal): Promise<Interaction> => {
    const fileSearchTool = {
      type: 'file_search' as const,
      file_search_store_names: [input.storeName],
      ...(input.metadataFilter ? { metadata_filter: input.metadataFilter } : {}),
    };
    try {
      return (await client.interactions.create(
        {
          model: input.model,
          input: input.prompt,
          tools: [fileSearchTool],
          response_format: {
            type: 'text',
            mime_type: 'application/json',
            schema: fileSearchDraftSchema,
          },
          generation_config: { max_output_tokens: 2_000, tool_choice: 'any' },
          store: false,
        },
        {
          maxRetries: 0,
          timeout: 50_000,
          fetchOptions: { signal },
        }
      )) as unknown as Interaction;
    } catch (error) {
      if (error instanceof ChatDiagnosticError) throw error;
      throw new ChatDiagnosticError(
        'Gemini no disponible',
        providerDiagnostic('gemini', 'interactions.create', error)
      );
    }
  };
};

/**
 * Registra en el ledger un turno resuelto con una respuesta editorial. Sin esto,
 * el servidor no sabe que la conversación existe —el texto se resuelve en el
 * navegador— y un seguimiento sobre ella llega sin ningún antecedente.
 *
 * El cuerpo solo dice QUÉ respuesta se mostró; el texto sale del catálogo del
 * servidor. Así el ledger no puede acabar guardando contenido del cliente.
 */

import { createClient } from '@supabase/supabase-js';
import { editorialTurn } from './chat/editorial-answers';
import {
  conversationAccessHash,
  validConversationAccessToken,
  validCountryPath,
  validIdentifier,
} from './chat/request-identifiers';
import {
  type EditorialTurnInput,
  SupabaseChatStore,
  type SupabaseRpcClient,
} from './chat/supabase-chat-store';

const MAX_BODY_BYTES = 4_000;
/** `chat-editorial-<id>` no puede superar los 128 caracteres del ledger. */
const MAX_MESSAGE_ID_CHARS = 113;

export interface ChatEditorialDependencies {
  enabled: boolean;
  recordEditorial(input: EditorialTurnInput): Promise<void>;
}

const errorResponse = (status: number, error: string) =>
  Response.json({ error }, { status, headers: { 'cache-control': 'no-store' } });

const parseEditorial = async (request: Request): Promise<EditorialTurnInput | null> => {
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_BODY_BYTES) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== 'object') return null;
  const candidate = parsed as Record<string, unknown>;
  if (
    !validIdentifier(candidate.conversation_id) ||
    !validConversationAccessToken(candidate.conversation_access_token) ||
    !validIdentifier(candidate.user_message_id) ||
    candidate.user_message_id.length > MAX_MESSAGE_ID_CHARS ||
    !validCountryPath(candidate.country_path)
  ) {
    return null;
  }
  const turn = editorialTurn(candidate.answer_id);
  if (!turn) return null;
  return {
    conversationId: candidate.conversation_id,
    conversationAccessHash: await conversationAccessHash(candidate.conversation_access_token),
    userMessageId: candidate.user_message_id,
    countryPath: candidate.country_path,
    ...turn,
  };
};

export const createChatEditorialHandler =
  (dependencies: ChatEditorialDependencies) =>
  async (request: Request): Promise<Response> => {
    if (request.method !== 'POST') return errorResponse(405, 'Método no permitido');
    if (!dependencies.enabled) return errorResponse(503, 'Registro no disponible');
    const turn = await parseEditorial(request);
    if (!turn) return errorResponse(400, 'Turno editorial inválido');
    try {
      await dependencies.recordEditorial(turn);
      return new Response(null, { status: 204, headers: { 'cache-control': 'no-store' } });
    } catch {
      // El diagnóstico del ledger no sale al navegador: puede traer el DSN.
      return errorResponse(503, 'Registro no disponible');
    }
  };

const createProductionEditorialDependencies = (
  environment: NodeJS.ProcessEnv = process.env
): ChatEditorialDependencies => {
  const supabaseUrl = environment.SUPABASE_URL?.trim();
  const supabaseSecretKey = environment.SUPABASE_SECRET_KEY?.trim();
  if (
    environment.CHAT_COMPARISON_ENABLED !== 'true' ||
    !supabaseUrl?.startsWith('https://') ||
    !supabaseSecretKey
  ) {
    return {
      enabled: false,
      async recordEditorial() {},
    };
  }
  const supabase = createClient(supabaseUrl, supabaseSecretKey, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  });
  const client: SupabaseRpcClient = {
    async rpc(functionName, parameters) {
      const { data, error } = await supabase.rpc(functionName, parameters);
      return { data, error: error ? { message: error.message, code: error.code } : null };
    },
  };
  // El experimento se declara igual que en el chat, pero un turno editorial no
  // compite en la comparación: se distingue por `strategy` en `chat_messages`.
  const store = new SupabaseChatStore(client, {
    experiment_version: 'editorial-2026-08-05-v1',
    deployed_commit:
      environment.COMMIT_REF?.trim() || environment.DEPLOY_ID?.trim() || 'local-development',
    comparison_schema_version: 'residenciafiscal-chat-comparison/1',
    structured_corpus_version: 'editorial',
    structured_prompt_version: 'editorial',
    file_search_store: 'editorial',
    file_search_prompt_version: 'editorial',
  });
  return { enabled: true, recordEditorial: (input) => store.recordEditorial(input) };
};

export default createChatEditorialHandler(createProductionEditorialDependencies());

export const config = {
  path: '/api/chat-editorial',
  method: 'POST',
  rateLimit: {
    aggregateBy: ['ip', 'domain'],
    windowSize: 60,
    windowLimit: 10,
  },
};

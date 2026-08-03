import { createClient } from '@supabase/supabase-js';
import {
  type ChatVoteInput,
  type ChatVoteReason,
  type ChatVoteVerdict,
  SupabaseChatVoteStore,
  type SupabaseRpcClient,
} from './chat/supabase-chat-store';

const MAX_BODY_BYTES = 2_000;
const VERDICTS = new Set<ChatVoteVerdict>(['a', 'b', 'c', 'tie', 'both_bad']);
const REASONS = new Set<ChatVoteReason>([
  'better_grounding',
  'clearer',
  'more_complete',
  'better_limits',
  'no_preference',
  'both_inadequate',
]);

export interface ChatVoteDependencies {
  enabled: boolean;
  vote(input: ChatVoteInput): Promise<boolean>;
}

const errorResponse = (status: number, error: string) =>
  Response.json({ error }, { status, headers: { 'cache-control': 'no-store' } });

const parseVote = async (request: Request): Promise<ChatVoteInput | null> => {
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
    typeof candidate.request_id !== 'string' ||
    !/^chat-[\w-]{1,123}$/.test(candidate.request_id) ||
    typeof candidate.verdict !== 'string' ||
    !VERDICTS.has(candidate.verdict as ChatVoteVerdict) ||
    typeof candidate.reason !== 'string' ||
    !REASONS.has(candidate.reason as ChatVoteReason) ||
    Object.keys(candidate).some((key) => !['request_id', 'verdict', 'reason'].includes(key))
  ) {
    return null;
  }
  return {
    requestId: candidate.request_id,
    verdict: candidate.verdict as ChatVoteVerdict,
    reason: candidate.reason as ChatVoteReason,
  };
};

export const createChatVoteHandler =
  (dependencies: ChatVoteDependencies) =>
  async (request: Request): Promise<Response> => {
    if (request.method !== 'POST') return errorResponse(405, 'Método no permitido');
    if (!dependencies.enabled) return errorResponse(503, 'Voto no disponible');
    const vote = await parseVote(request);
    if (!vote) return errorResponse(400, 'Voto inválido');
    try {
      const created = await dependencies.vote(vote);
      if (!created) return errorResponse(409, 'La comparación ya tiene voto');
      return new Response(null, { status: 204, headers: { 'cache-control': 'no-store' } });
    } catch {
      return errorResponse(503, 'Voto no disponible');
    }
  };

const createProductionVoteDependencies = (
  environment: NodeJS.ProcessEnv = process.env
): ChatVoteDependencies => {
  const supabaseUrl = environment.SUPABASE_URL?.trim();
  const supabaseSecretKey = environment.SUPABASE_SECRET_KEY?.trim();
  if (
    environment.CHAT_COMPARISON_ENABLED !== 'true' ||
    !supabaseUrl?.startsWith('https://') ||
    !supabaseSecretKey
  ) {
    return {
      enabled: false,
      async vote() {
        return false;
      },
    };
  }
  const supabase = createClient(supabaseUrl, supabaseSecretKey, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  });
  const client: SupabaseRpcClient = {
    async rpc(functionName, parameters) {
      const { data, error } = await supabase.rpc(functionName, parameters);
      return { data, error: error ? { message: error.message } : null };
    },
  };
  const store = new SupabaseChatVoteStore(client);
  return { enabled: true, vote: (input) => store.vote(input) };
};

export default createChatVoteHandler(createProductionVoteDependencies());

export const config = {
  path: '/api/chat-vote',
  method: 'POST',
  rateLimit: {
    aggregateBy: ['ip', 'domain'],
    windowSize: 60,
    windowLimit: 10,
  },
};

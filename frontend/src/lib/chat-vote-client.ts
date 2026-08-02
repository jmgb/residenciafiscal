export type ChatVoteVerdict = 'a' | 'b' | 'tie' | 'both_bad';
export type ChatVoteReason =
  | 'better_grounding'
  | 'clearer'
  | 'more_complete'
  | 'better_limits'
  | 'no_preference'
  | 'both_inadequate';

interface ChatVoteInput {
  requestId: string;
  verdict: ChatVoteVerdict;
  reason: ChatVoteReason;
}

export type ChatVoteResult = 'recorded' | 'already_recorded';

export const submitChatVote = async (input: ChatVoteInput): Promise<ChatVoteResult> => {
  const response = await fetch('/api/chat-vote', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      request_id: input.requestId,
      verdict: input.verdict,
      reason: input.reason,
    }),
  });
  if (response.status === 204) return 'recorded';
  if (response.status === 409) return 'already_recorded';
  throw new Error('No se pudo registrar la valoración');
};

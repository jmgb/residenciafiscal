import { useState } from 'react';
import { type ChatVoteReason, type ChatVoteVerdict, submitChatVote } from '@/lib/chat-vote-client';
import { Button } from '@/shared/components/ui/button';

const VERDICTS: Array<{ value: ChatVoteVerdict; label: string }> = [
  { value: 'a', label: 'Opción A' },
  { value: 'b', label: 'Opción B' },
  { value: 'tie', label: 'Empate' },
  { value: 'both_bad', label: 'Ambas insuficientes' },
];

const PREFERENCE_REASONS: Array<{ value: ChatVoteReason; label: string }> = [
  { value: 'better_grounding', label: 'Mejor fundamentada' },
  { value: 'clearer', label: 'Más clara' },
  { value: 'more_complete', label: 'Más completa' },
  { value: 'better_limits', label: 'Explica mejor sus límites' },
];

type SubmissionState = 'idle' | 'submitting' | 'recorded' | 'already_recorded' | 'error';

interface ChatComparisonVoteProps {
  comparisonId: string;
}

const automaticReason = (verdict: ChatVoteVerdict): ChatVoteReason | '' => {
  if (verdict === 'tie') return 'no_preference';
  if (verdict === 'both_bad') return 'both_inadequate';
  return '';
};

export const ChatComparisonVote = ({ comparisonId }: ChatComparisonVoteProps) => {
  const [verdict, setVerdict] = useState<ChatVoteVerdict | ''>('');
  const [reason, setReason] = useState<ChatVoteReason | ''>('');
  const [submission, setSubmission] = useState<SubmissionState>('idle');

  const selectVerdict = (value: ChatVoteVerdict) => {
    setVerdict(value);
    setReason(automaticReason(value));
    setSubmission('idle');
  };

  const submit = async () => {
    if (!verdict || !reason || submission === 'submitting') return;
    setSubmission('submitting');
    try {
      setSubmission(await submitChatVote({ requestId: comparisonId, verdict, reason }));
    } catch {
      setSubmission('error');
    }
  };

  return (
    <section
      aria-label='Valorar comparación'
      className='rounded-xl border border-primary-200 bg-primary-50 p-4'
    >
      <h3 className='font-heading text-sm font-semibold text-foreground'>
        ¿Qué respuesta es mejor?
      </h3>
      <p className='mt-1 text-xs leading-relaxed text-secondary-foreground'>
        Valora la calidad de las respuestas, no el proveedor. El voto no sustituye la revisión de
        las citas.
      </p>

      {submission === 'recorded' || submission === 'already_recorded' ? (
        <p role='status' className='mt-3 rounded-lg bg-background px-3 py-2 text-sm font-medium'>
          {submission === 'recorded'
            ? 'Valoración registrada. Gracias por comparar las dos opciones.'
            : 'Esta comparación ya tenía una valoración registrada.'}
        </p>
      ) : (
        <>
          <fieldset className='mt-3'>
            <legend className='sr-only'>Respuesta preferida</legend>
            <div className='grid grid-cols-2 gap-2 sm:grid-cols-4'>
              {VERDICTS.map((item) => (
                <label
                  key={item.value}
                  className='flex cursor-pointer items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-xs font-medium has-checked:border-primary has-checked:bg-primary-100'
                >
                  <input
                    type='radio'
                    name={`chat-vote-${comparisonId}`}
                    value={item.value}
                    checked={verdict === item.value}
                    onChange={() => selectVerdict(item.value)}
                    className='accent-primary'
                  />
                  {item.label}
                </label>
              ))}
            </div>
          </fieldset>

          {(verdict === 'a' || verdict === 'b') && (
            <label className='mt-3 block text-xs font-medium text-secondary-foreground'>
              Motivo
              <select
                aria-label='Motivo'
                value={reason}
                onChange={(event) => setReason(event.target.value as ChatVoteReason)}
                className='mt-1.5 h-10 w-full rounded-lg border border-input bg-background px-3 text-sm control-focus'
              >
                <option value=''>Selecciona un motivo</option>
                {PREFERENCE_REASONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          )}

          {submission === 'error' && (
            <p role='alert' className='mt-3 text-xs font-medium text-destructive'>
              No se pudo registrar. Puedes volver a intentarlo.
            </p>
          )}

          <div className='mt-3 flex flex-wrap items-center justify-between gap-3'>
            <p className='text-[0.6875rem] text-muted-foreground'>
              Sin texto libre ni datos personales.
            </p>
            <Button
              type='button'
              size='sm'
              onClick={submit}
              disabled={!verdict || !reason || submission === 'submitting'}
            >
              {submission === 'submitting' ? 'Enviando…' : 'Enviar valoración'}
            </Button>
          </div>
        </>
      )}
    </section>
  );
};

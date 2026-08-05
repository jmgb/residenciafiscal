import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ChatBubble } from '@/components/chat/ChatBubble';
import { DeepResearchCard } from '@/components/chat/DeepResearchCard';
import type { DeepResearchJob } from '@/types/chat';

const completed: DeepResearchJob = {
  jobId: 'deep-1',
  status: 'completed',
  stage: 'completed',
  result: {
    schemaVersion: 'residenciafiscal-deep-research-output/2',
    jobId: 'deep-1',
    requestId: 'deep-1',
    status: 'completa',
    text: 'La prueba debe ser coherente.\n\nLa valoración depende del conjunto probatorio.',
    limits: ['No sustituye asesoramiento profesional.'],
    claims: [
      { text: 'La prueba debe ser\ncoherente.', evidenceIndexes: [1] },
      { text: 'La valoración depende del conjunto probatorio.', evidenceIndexes: [2] },
    ],
    evidence: [
      {
        judgmentId: 'sts-1',
        page: 3,
        sourceSha256: 'a'.repeat(64),
        quote: 'La prueba debe ser\ncoherente.',
        verification: 'EXACT',
      },
      {
        judgmentId: 'san-2',
        page: 8,
        sourceSha256: 'b'.repeat(64),
        quote: 'La valoración depende del conjunto probatorio.',
        verification: 'EXACT',
      },
    ],
    costMicrousd: 1200,
    costMeasurement: 'ACTUAL',
    pricingVersion: 'test-catalog',
    model: 'gpt-5.6-luna',
    reasoningEffort: 'high',
    latencyMs: 4200,
  },
};

describe('DeepResearchCard', () => {
  it('shows progress states without exposing chain of thought', () => {
    render(
      <DeepResearchCard
        job={{ jobId: 'deep-1', status: 'running', stage: 'verifying', result: null }}
        onCancel={() => undefined}
      />
    );

    expect(screen.getByRole('status')).toHaveTextContent('Verificando');
    expect(
      screen.getByRole('button', { name: 'Cancelar investigación profunda' })
    ).toBeInTheDocument();
    expect(
      screen.queryByText('La respuesta A/B sigue separada de esta investigación.')
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/razonamiento|cadena de pensamiento/i)).not.toBeInTheDocument();
  });

  it('shows a cancellation failure without hiding the active job or retry button', () => {
    render(
      <DeepResearchCard
        job={{
          jobId: 'deep-1',
          status: 'running',
          stage: 'reading',
          result: null,
          error: 'No se ha podido cancelar la investigación.',
        }}
        onCancel={() => undefined}
      />
    );

    expect(screen.getByRole('alert')).toHaveTextContent(
      'No se ha podido cancelar la investigación.'
    );
    expect(
      screen.getByRole('button', { name: 'Cancelar investigación profunda' })
    ).toBeInTheDocument();
  });

  it('shows immediate cancellation feedback and blocks repeated clicks', () => {
    render(
      <DeepResearchCard
        job={{
          jobId: 'deep-1',
          status: 'running',
          stage: 'reading',
          result: null,
          cancellationRequested: true,
        }}
        onCancel={() => undefined}
      />
    );

    expect(screen.getByRole('status')).toHaveTextContent('Cancelando investigación profunda');
    const button = screen.getByRole('button', { name: 'Cancelando investigación profunda' });
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent('Cancelando');
  });

  it('renders conclusions, evidence and scope as separate readable blocks', () => {
    render(
      <DeepResearchCard
        job={{ ...completed, comparisonId: 'chat-comparison-1' }}
        comparisonId='chat-comparison-1'
        onCancel={() => undefined}
      />
    );

    expect(screen.getByRole('status')).toHaveTextContent('Investigación profunda completada');
    expect(screen.getByRole('heading', { name: 'Respuesta verificada' })).toBeInTheDocument();
    const claims = screen.getAllByTestId('deep-research-claim');
    expect(claims).toHaveLength(2);
    expect(claims[0]).toHaveTextContent('La prueba debe ser coherente.');
    expect(claims[0]).toHaveClass('whitespace-normal');
    expect(claims[1]).toHaveTextContent('La valoración depende del conjunto probatorio.');

    expect(screen.getByRole('heading', { name: 'Evidencias verificadas' })).toBeInTheDocument();
    const evidence = screen.getAllByTestId('deep-research-evidence');
    expect(evidence).toHaveLength(2);
    expect(evidence[0].querySelector('blockquote')).toHaveClass('whitespace-normal');
    expect(screen.getByText('STS 1 · página 3')).toHaveClass('font-mono');
    expect(screen.getByText('SAN 2 · página 8')).toBeInTheDocument();
    const scopeHeading = screen.getByRole('heading', { name: 'Alcance del análisis' });
    expect(scopeHeading).toBeInTheDocument();
    expect(scopeHeading.closest('section')?.querySelector('ul')).toHaveClass(
      'text-secondary-foreground'
    );
    expect(screen.getByText('No sustituye asesoramiento profesional.')).toBeInTheDocument();
    expect(screen.getByText(/Coste real: 0,00 USD/)).toBeInTheDocument();
    expect(screen.getByText(/Respuesta en: 4 s/)).toBeInTheDocument();
    expect(screen.getByText('Modelo: gpt-5.6-luna high')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Opción C' })).toBeInTheDocument();
  });

  it('renders Markdown formatting inside verified conclusions', () => {
    const result = completed.result;
    if (!result) throw new Error('Expected a completed deep-research result');

    render(
      <DeepResearchCard
        job={{
          ...completed,
          result: {
            ...result,
            claims: [
              {
                text: '**Respuesta breve.** La conclusión está verificada.',
                evidenceIndexes: [1],
              },
            ],
          },
        }}
        onCancel={() => undefined}
      />
    );

    const claim = screen.getByTestId('deep-research-claim');
    expect(claim).toHaveTextContent('Respuesta breve. La conclusión está verificada.');
    expect(claim).not.toHaveTextContent('**');
    expect(claim.querySelector('strong')).toHaveTextContent('Respuesta breve.');
  });

  it('uses the full chat width without nesting the research card in another surface', () => {
    render(
      <ChatBubble
        message={{
          id: 'assistant-deep-1',
          role: 'assistant',
          content: completed.result?.text ?? '',
          createdAt: '2026-08-04T10:00:00.000Z',
          deepResearch: completed,
        }}
      />
    );

    const bubble = screen.getByTestId('chat-bubble-assistant');
    expect(bubble).toHaveClass('w-full', 'max-w-full');
    expect(bubble).not.toHaveClass('border', 'px-3.5', 'py-2.5', 'shadow-sm');
  });
});

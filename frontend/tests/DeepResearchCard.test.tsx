import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DeepResearchCard } from '@/components/chat/DeepResearchCard';
import type { DeepResearchJob } from '@/types/chat';

const completed: DeepResearchJob = {
  jobId: 'deep-1',
  status: 'completed',
  stage: 'completed',
  result: {
    schemaVersion: 'residenciafiscal-deep-research-output/1',
    jobId: 'deep-1',
    requestId: 'deep-1',
    status: 'completa',
    text: 'Conclusión con respaldo documental.',
    limits: ['No sustituye asesoramiento profesional.'],
    claims: [{ text: 'La prueba debe ser coherente.', evidenceIndexes: [1] }],
    evidence: [
      {
        judgmentId: 'sts-1',
        page: 3,
        sourceSha256: 'a'.repeat(64),
        quote: 'Cita literal verificable.',
        verification: 'EXACT',
      },
    ],
    costMicrousd: 1200,
    costMeasurement: 'ACTUAL',
    model: 'gpt-5.6',
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
    expect(screen.queryByText(/razonamiento|cadena de pensamiento/i)).not.toBeInTheDocument();
  });

  it('renders the completed answer, evidence, limits, cost and latency', () => {
    render(
      <DeepResearchCard
        job={{ ...completed, comparisonId: 'chat-comparison-1' }}
        comparisonId='chat-comparison-1'
        onCancel={() => undefined}
      />
    );

    expect(screen.getByRole('status')).toHaveTextContent('Investigación profunda completada');
    expect(screen.getByText('Conclusión con respaldo documental.')).toBeInTheDocument();
    expect(screen.getByText('STS 1 · página 3')).toBeInTheDocument();
    expect(screen.getByText(/Cita literal verificable\./)).toBeInTheDocument();
    expect(screen.getByText(/Coste real: 0,0012 USD/)).toBeInTheDocument();
    expect(screen.getByText(/Respuesta en: 4,2 s/)).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Opción C' })).toBeInTheDocument();
  });
});
